import os
import re
import psutil
from kubernetes import client, config

class AutoRemediationAgent:
    def __init__(self):
        # Load local kubeconfig
        try:
            config.load_kube_config()
            self.v1 = client.CoreV1Api()
            self.active = True
        except Exception as e:
            print(f"Could not load kubeconfig. Remediation offline. Error: {e}")
            self.active = False

    def terminate_pod(self, pod_name: str, namespace: str = "test-apps"):
        """
        Terminates the anomalous entity. If it is a host process (e.g. Chrome[1234]),
        terminates it using psutil. Otherwise, sends a delete signal to the Kubernetes API.
        """
        # 1. Try to terminate as host process if name contains [PID]
        match = re.search(r"\[(\d+)\]", pod_name)
        if match:
            pid = int(match.group(1))
            try:
                p = psutil.Process(pid)
                p.kill()  # Force kill to ensure remediation completes immediately
                return {
                    "status": "success",
                    "message": f"Successfully self-healed: terminated host process '{pod_name}' (PID: {pid})."
                }
            except psutil.NoSuchProcess:
                return {"status": "error", "message": f"Process with PID {pid} was not found. It may have already exited."}
            except psutil.AccessDenied:
                return {"status": "error", "message": f"Access denied. Cannot terminate process with PID {pid}. Try running as Administrator."}
            except Exception as e:
                return {"status": "error", "message": f"Error during process self-healing: {str(e)}"}

        # 2. Kubernetes API fallback
        if not self.active:
            return {"status": "error", "message": "Kubernetes API not connected. Cannot perform remediation."}
            
        try:
            self.v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            return {
                "status": "success", 
                "message": f"Successfully sent termination signal for rogue pod '{pod_name}'. The cluster is self-healing."
            }
        except client.exceptions.ApiException as e:
            return {"status": "error", "message": f"Failed to terminate pod: {e.reason}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
