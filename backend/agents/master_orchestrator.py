import os
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

        if status == "error":
            return "The AI Orchestrator cannot evaluate cluster health because telemetry data from Prometheus is currently unavailable."

        if len(anomalies) == 0:
            prompt = f"""
            You are an expert Kubernetes Site Reliability Engineer (SRE) and AI Agent. 
            You just analyzed {total_pods} pods using an Isolation Forest ML model. No anomalies were found. 
            Provide a very brief 2-sentence confirmation to the human operator that the cluster is healthy and resource utilization is normal.
            """
        else:
            anomaly_details = "\n".join([f"- Pod: {a['pod']} (CPU Rate: {a['cpu_usage_core_rate']}, Memory: {a['memory_usage_bytes']} bytes)" for a in anomalies])
            prompt = f"""
            You are an expert Kubernetes Site Reliability Engineer (SRE) and AI Agent.
            You just analyzed {total_pods} pods and found {len(anomalies)} critical anomalies using your Isolation Forest model.
            
            Here is the raw data for the anomalous pods:
            {anomaly_details}
            
            Provide a concise, 3-sentence professional analysis for the dashboard. 
            Explain what this might mean (e.g. memory leak, CPU spike, infinite loop) and recommend exactly what the human operator should do next to investigate or mitigate the issue.
            Do not use markdown bolding in your response, keep it as plain text.
            """

        return self._call_gemini_with_fallback(prompt)

    def chat_with_assistant(self, user_message: str, cluster_context: dict) -> str:
        """
        A conversational interface allowing the user to directly interrogate the AI agents.
        """
        if not self.all_keys:
            return "Agentic LLM offline. Please add your GEMINI_API_KEY to the .env file."
            
        anomalies = cluster_context.get('anomalies', [])
        logs = cluster_context.get('log_keywords', [])
        
        prompt = f"""
        You are 'Kube AI', an advanced AI-powered Kubernetes Intelligence conversational assistant.
        The user is asking you a question about their live Kubernetes cluster.
        
        Current Live Cluster Context (gathered from your ML Agents):
        - Anomalous Pods Detected: {anomalies if anomalies else 'None'}
        - Dominant NLP Error Patterns in Logs: {logs if logs else 'None'}
        
        User's Question: "{user_message}"
        
        Answer the question professionally, concisely, and accurately based ONLY on the provided context.
        If the user asks "Which pod caused the CPU spike?", look at the Anomalous Pods list.
        If they ask about errors, look at the NLP Log Patterns.
        Keep the answer to 2 or 3 short sentences. Do not use markdown bolding.
        """
        return self._call_gemini_with_fallback(prompt)

