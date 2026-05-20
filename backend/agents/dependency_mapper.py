import networkx as nx
from .prometheus_client import PrometheusConnector

class DependencyMapper:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.prom_client = PrometheusConnector()

    def get_topology(self):
        """
        Dynamically builds the service dependency graph using NetworkX.
        For live system metrics, maps all running processes to the host OS.
        """
        self.graph.clear()
        
        cpu_raw = self.prom_client.get_pod_cpu_usage()
        pods = [item["metric"].get("pod", "unknown") for item in cpu_raw]
        
        # Detect anomalies to highlight anomalous pods dynamically on the map
        anomalous_pods = []
        try:
            from .anomaly_detector import ResourceAnomalyDetector
            detector = ResourceAnomalyDetector()
            detection_result = detector.analyze_current_state()
            if isinstance(detection_result, dict) and detection_result.get("status") == "success":
                anomalous_pods = [a["pod"] for a in detection_result.get("anomalies", [])]
        except Exception as e:
            print(f"Error checking anomalies in dependency mapper: {e}")
        
        # Map out the host machine
        self.graph.add_node("localhost", type="ingress")
        
        for pod in pods:
            node_type = "anomaly" if pod in anomalous_pods else "service"
            self.graph.add_node(pod, type=node_type)
            self.graph.add_edge("localhost", pod, weight=5)
        
        # Transform the NetworkX DiGraph into Cytoscape.js format for the frontend
        elements = []
        for node, data in self.graph.nodes(data=True):
            elements.append({"data": {"id": node, "label": node, "type": data.get("type", "service")}})
            
        for source, target, data in self.graph.edges(data=True):
            elements.append({"data": {"source": source, "target": target, "weight": data.get("weight", 1)}})
            
        return {"elements": elements}
