import os
import re
import psutil
import yaml
from kubernetes import client, config

class AutoRemediationAgent:
    def __init__(self):
        # Load local kubeconfig
        try:
            # Check if running in a container with mounted kubeconfig
            container_kube_path = "/root/.kube/config"
            if os.path.exists(container_kube_path):
                print(f"Detected mounted Kubernetes config at {container_kube_path}. Rewriting for container environment...")
                with open(container_kube_path, 'r') as f:
                    cfg = yaml.safe_load(f)
                
                # Rewrite server host to host.docker.internal to access host's API server
                for cluster_entry in cfg.get("clusters", []):
                    server = cluster_entry.get("cluster", {}).get("server", "")
                    if "127.0.0.1" in server or "localhost" in server:
                        # e.g., https://127.0.0.1:63149 -> https://host.docker.internal:63149
                        server = server.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal")
                        cluster_entry["cluster"]["server"] = server
                    
                    # Rewrite absolute Windows ca.crt path to the Linux container path
                    ca = cluster_entry.get("cluster", {}).get("certificate-authority", "")
                    if ca:
                        ca_rewritten = ca.replace("C:\\Users\\prane\\.minikube", "/root/.minikube").replace("C:/Users/prane/.minikube", "/root/.minikube").replace("\\", "/")
                        cluster_entry["cluster"]["certificate-authority"] = ca_rewritten

                # Rewrite absolute Windows user certificate/key paths
                for user_entry in cfg.get("users", []):
                    user_client = user_entry.get("user", {})
                    cc = user_client.get("client-certificate", "")
                    ck = user_client.get("client-key", "")
                    if cc:
                        user_client["client-certificate"] = cc.replace("C:\\Users\\prane\\.minikube", "/root/.minikube").replace("C:/Users/prane/.minikube", "/root/.minikube").replace("\\", "/")
                    if ck:
                        user_client["client-key"] = ck.replace("C:\\Users\\prane\\.minikube", "/root/.minikube").replace("C:/Users/prane/.minikube", "/root/.minikube").replace("\\", "/")
                
                # Save transformed configuration to temporary file
                temp_cfg = "/tmp/k8s_kubeconfig"
                os.makedirs(os.path.dirname(temp_cfg), exist_ok=True)
                with open(temp_cfg, "w") as f:
                    yaml.safe_dump(cfg, f)
                
                config.load_kube_config(config_file=temp_cfg)
                
                # Disable SSL hostname verification for host.docker.internal mismatch
                c = client.Configuration.get_default_copy()
                c.assert_hostname = False
                client.Configuration.set_default(c)
                
                print("Kubernetes API config rewritten and loaded successfully in container (hostname check bypassed).")
            else:
                # Direct host-level execution (e.g. running python locally outside Docker)
                config.load_kube_config()
                print("Kubernetes API config loaded successfully on host.")

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
