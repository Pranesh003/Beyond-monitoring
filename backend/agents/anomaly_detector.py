import numpy as np
from sklearn.ensemble import IsolationForest
from .prometheus_client import PrometheusConnector

class ResourceAnomalyDetector:
    def __init__(self):
        self.prom_client = PrometheusConnector()
        # Contamination controls the expected proportion of anomalies in the dataset
        self.model = IsolationForest(contamination=0.1, random_state=42)

    def analyze_current_state(self):
        """
        Pulls metrics from Prometheus, extracts features, and runs Isolation Forest 
        to detect pods acting abnormally compared to the rest of the cluster.
        """
        cpu_data = self.prom_client.get_pod_cpu_usage()
        mem_data = self.prom_client.get_pod_memory_usage()

        if not cpu_data or not mem_data:
            return {"status": "error", "message": "Could not connect to Prometheus or no data returned"}

        # Extract numerical features for ML processing
        pods = []
        features = []
        
        # Map memory values by pod name for easy lookup
        mem_dict = {item['metric'].get('pod', 'unknown'): float(item['value'][1]) for item in mem_data}

        for item in cpu_data:
            pod_name = item['metric'].get('pod', 'unknown')
            cpu_val = float(item['value'][1])
            mem_val = mem_dict.get(pod_name, 0.0)
            
            pods.append(pod_name)
            features.append([cpu_val, mem_val])

        if not features:
             return {"status": "ok", "anomalies": []}

        X = np.array(features)
        
        # Isolation forest requires a few samples to establish a baseline of "normal".
        # If there are too few pods running, return early to avoid false positives.
        if len(X) < 3:
             return {
                 "status": "ok", 
                 "message": "Not enough pods running to establish a reliable baseline for anomalies.", 
                 "anomalies": []
             }

        # Train model on current state and predict (-1 means anomaly, 1 means normal)
        self.model.fit(X)
        predictions = self.model.predict(X)
        
        # Decision function gives a continuous score (lower score = more anomalous)
        scores = self.model.decision_function(X)

        anomalies = []
        for i, pred in enumerate(predictions):
            if pred == -1:
                anomalies.append({
                    "pod": pods[i],
                    "cpu_usage_core_rate": round(features[i][0], 5),
                    "memory_usage_bytes": features[i][1],
                    "anomaly_score": round(float(scores[i]), 4),
                    "agent_reasoning": "This pod's resource profile falls significantly outside the cluster baseline."
                })

        return {
            "status": "success",
            "total_pods_analyzed": len(pods),
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies
        }
