import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class MasterOrchestrator:
    def __init__(self):
        # Load primary key and any backup keys
        self.primary_key = os.getenv("GEMINI_API_KEY")
        backup_keys_str = os.getenv("GEMINI_BACKUP_KEYS", "")
        self.backup_keys = [k.strip() for k in backup_keys_str.split(",") if k.strip()]
        
        # Combine all unique keys into a list of working candidates
        self.all_keys = []
        if self.primary_key:
            self.all_keys.append(self.primary_key)
        for bk in self.backup_keys:
            if bk not in self.all_keys:
                self.all_keys.append(bk)
                
        self.current_key_index = 0
        self.model = None
        
        # Cache layer for API savings and rate-limit prevention
        self._last_anomalies = None
        self._last_insight = None
        self._last_insight_time = 0
        
        self._initialize_model()

    def _initialize_model(self) -> bool:
        if not self.all_keys:
            print("No Gemini API keys configured.")
            self.model = None
            return False
            
        key = self.all_keys[self.current_key_index]
        try:
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            print(f"Configured Gemini with API key ending in ...{key[-6:]}")
            return True
        except Exception as e:
            print(f"Error configuring Gemini with API key ending in ...{key[-6:]}: {e}")
            self.model = None
            return False

    def _call_gemini_with_fallback(self, prompt: str) -> str:
        if not self.all_keys:
            return "Agentic LLM offline. Please configure a GEMINI_API_KEY."

        attempts = 0
        max_attempts = len(self.all_keys)
        
        while attempts < max_attempts:
            if not self.model:
                self._initialize_model()
                
            if not self.model:
                # If model initialization failed, rotate to the next key
                attempts += 1
                self.current_key_index = (self.current_key_index + 1) % len(self.all_keys)
                continue
                
            key = self.all_keys[self.current_key_index]
            masked_key = f"...{key[-6:]}" if len(key) >= 6 else "invalid"
            print(f"Attempting LLM generation with API key ending in {masked_key} (attempt {attempts + 1}/{max_attempts})")
            
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"Error with API key ending in {masked_key}: {e}")
                # Rotate to the next key
                attempts += 1
                self.current_key_index = (self.current_key_index + 1) % len(self.all_keys)
                self.model = None  # Force re-initialization on next loop iteration
                
        return "The Master AI experienced errors across all configured API keys. LLM generation failed."

    def generate_insight(self, anomaly_data: dict) -> str:
        if not self.all_keys:
            return "Agentic LLM offline. Please provide a GEMINI_API_KEY in the backend .env file to enable natural-language insights."

        status = anomaly_data.get("status", "error")
        total_pods = anomaly_data.get("total_pods_analyzed", 0)
        anomalies = anomaly_data.get("anomalies", [])
        storage_anoms = anomaly_data.get("storage_anomalies", [])
        network_anoms = anomaly_data.get("network_anomalies", [])
        predictions = anomaly_data.get("predictions", [])
        scaling_reqs = anomaly_data.get("scaling_requirements", [])
        storage_correlations = anomaly_data.get("storage_correlations", [])

        if status == "error":
            return "The AI Orchestrator cannot evaluate cluster health because telemetry data from Prometheus is currently unavailable."

        # OPTIMIZATION 1: If there are zero anomalies and no storage/network alerts, return a premium static summary.
        if len(anomalies) == 0 and len(storage_anoms) == 0 and len(network_anoms) == 0:
            return f"Cluster is operating within normal baseline limits. The Isolation Forest ML model analyzed all {total_pods} active pods/processes and detected no resource utilization anomalies. Network and Storage paths remain stable."

        # OPTIMIZATION 2: Caching layer for active anomalies.
        current_anomaly_signatures = sorted([a.get('pod', '') for a in anomalies]) + sorted([s.get('entity', '') for s in storage_anoms])
        
        now = time.time()
        if (self._last_anomalies == current_anomaly_signatures and 
            self._last_insight and 
            (now - self._last_insight_time) < 60):
            print("Returning cached SRE anomaly insight to save API quota...")
            return self._last_insight

        # Otherwise, fetch a new dynamic SRE report from Gemini
        anomaly_details = "\n".join([f"- Pod: {a['pod']} (CPU Rate: {a['cpu_usage_core_rate']}, Memory: {a['memory_usage_bytes']} bytes)" for a in anomalies])
        storage_details = "\n".join([f"- Storage bottleneck: {s['message']} (Type: {s['type']}, Severity: {s['severity']})" for s in storage_anoms])
        network_details = "\n".join([f"- Network anomaly: {n['message']} (Link: {n['flow']})" for n in network_anoms])
        prediction_details = "\n".join([f"- Projected Crash Risk for {p['pod']}: {int(p['failure_probability']*100)}% (Indicators: {', '.join(p['leading_indicators'])})" for p in predictions])
        scaling_details = "\n".join([f"- Recommendation: {sr['action_details']}" for sr in scaling_reqs])

        prompt = f"""
        You are an expert Kubernetes Site Reliability Engineer (SRE) and AI Agent.
        You analyzed the cluster state and detected resources anomalies, storage bottlenecks, network anomalies, and forecasting failure models.
        
        Live Metric Indicators:
        Anomalous Pods (ML Outliers):
        {anomaly_details if anomalies else 'None detected'}
        
        Storage Bottlenecks:
        {storage_details if storage_anoms else 'None detected'}
        
        Network Anomalies:
        {network_details if network_anoms else 'None detected'}
        
        Failure Projections (1m/5m regressions):
        {prediction_details if predictions else 'None detected'}
        
        Autoscaling Actions:
        {scaling_details if scaling_reqs else 'None required'}
        
        Provide a concise, 3-sentence professional Root Cause Analysis (RCA) and mitigation plan for the dashboard.
        Correlate metrics (e.g. if a memory leak is projected or storage latency is high, explain the cascading impact) and advise exactly what the human operator should do.
        Do not use markdown bolding in your response, keep it as plain text.
        """

        insight = self._call_gemini_with_fallback(prompt)
        
        # Cache this new insight if it generated successfully
        if "failed" not in insight.lower() and "offline" not in insight.lower():
            self._last_anomalies = current_anomaly_signatures
            self._last_insight = insight
            self._last_insight_time = now

        return insight

    def chat_with_assistant(self, user_message: str, cluster_context: dict) -> str:
        """
        A conversational interface allowing the user to directly interrogate the AI agents.
        """
        if not self.all_keys:
            return "Agentic LLM offline. Please add your GEMINI_API_KEY to the .env file."
            
        anomalies = cluster_context.get('anomalies', [])
        logs = cluster_context.get('log_keywords', [])
        storage_anoms = cluster_context.get('storage_anomalies', [])
        network_anoms = cluster_context.get('network_anomalies', [])
        
        prompt = f"""
        You are 'Kube AI', an advanced AI-powered Kubernetes Intelligence conversational assistant.
        The user is asking you a question about their live Kubernetes cluster.
        
        Current Live Cluster Context (gathered from all active ML, Log, Network, Storage, and Forecasting Agents):
        - Anomalous Pods: {anomalies if anomalies else 'None'}
        - NLP Log Error Patterns: {logs if logs else 'None'}
        - Storage Bottlenecks: {storage_anoms if storage_anoms else 'None'}
        - Network Anomalies: {network_anoms if network_anoms else 'None'}
        
        User's Question: "{user_message}"
        
        Answer the question professionally, concisely, and accurately based ONLY on the provided context.
        If the user asks about network congestion, storage leaks, or process spikes, check the corresponding context fields.
        Keep the answer to 2 or 3 short sentences. Do not use markdown bolding.
        """
        return self._call_gemini_with_fallback(prompt)

