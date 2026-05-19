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
        
        # Map out the host machine
        self.graph.add_node("localhost", type="ingress")
        
        for pod in pods:
            self.graph.add_node(pod, type="service")
            self.graph.add_edge("localhost", pod, weight=5)
        
        # Transform the NetworkX DiGraph into Cytoscape.js format for the frontend
        elements = []
        for node, data in self.graph.nodes(data=True):
            elements.append({"data": {"id": node, "label": node, "type": data.get("type", "service")}})
            
        for source, target, data in self.graph.edges(data=True):
            elements.append({"data": {"source": source, "target": target, "weight": data.get("weight", 1)}})
            
        return {"elements": elements}
