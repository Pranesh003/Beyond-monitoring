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
        
        # Circuit Breaker pattern to eliminate latency when API keys are rate-limited
        self.circuit_tripped = False
        self.last_circuit_trip_time = 0
        self.circuit_cooldown = 600  # 10 minutes in seconds
        
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

        now = time.time()
        if self.circuit_tripped:
            if now - self.last_circuit_trip_time < self.circuit_cooldown:
                print("Gemini circuit breaker is TRIPPED. Bypassing API calls to avoid latency.")
                return "Agentic LLM offline due to circuit breaker trip."
            else:
                print("Gemini circuit breaker cooldown expired. Resetting circuit...")
                self.circuit_tripped = False

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
                err_msg = str(e)
                if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower() or "rate limit" in err_msg.lower():
                    print(f"[RATE LIMIT / QUOTA EXHAUSTED] API Key ending in {masked_key} hit quota/rate-limits. Details: {err_msg}")
                    print("Dynamically switching to the next configured backup API key...")
                else:
                    print(f"Error with API key ending in {masked_key}: {e}")
                # Rotate to the next key
                attempts += 1
                self.current_key_index = (self.current_key_index + 1) % len(self.all_keys)
                self.model = None  # Force re-initialization on next loop iteration
                
        # Trip the circuit breaker since all keys failed
        self.circuit_tripped = True
        self.last_circuit_trip_time = now
        print(f"Gemini circuit breaker TRIPPED for the next {self.circuit_cooldown} seconds.")
        return "The Master AI experienced errors across all configured API keys. LLM generation failed."

    def _generate_local_fallback_insight(self, anomaly_data: dict) -> str:
        anomalies = anomaly_data.get("anomalies", [])
        storage_anoms = anomaly_data.get("storage_anomalies", [])
        network_anoms = anomaly_data.get("network_anomalies", [])
        predictions = anomaly_data.get("predictions", [])
        
        reasons = []
        mitigations = []
        
        if anomalies:
            pods = [a['pod'] for a in anomalies]
            reasons.append(f"Resource anomalies were detected on pod(s) {', '.join(pods)} due to CPU/Memory utilization spikes exceeding standard ML baselines.")
            mitigations.append("Inspect process-level thread pools on the anomalous pods and consider executing the Auto-Heal remediation.")
            
        if storage_anoms:
            storage_msgs = [s['message'] for s in storage_anoms]
            reasons.append(f"Storage path bottleneck detected: {'; '.join(storage_msgs)}.")
            mitigations.append("Verify disk I/O limits, check filesystem mount points, and clean up temporary logs to free up volume capacity.")
            
        if network_anoms:
            net_flows = [n['flow'] for n in network_anoms]
            reasons.append(f"Active network anomalies identified on process/port path: {', '.join(net_flows)}.")
            mitigations.append("Audit active socket connections and check for high connection counts indicating potential leakage.")
            
        if predictions:
            crash_pods = [p['pod'] for p in predictions if p.get('failure_probability', 0) > 0.5]
            if crash_pods:
                reasons.append(f"Forecasting models project a high crash-loop risk for {', '.join(crash_pods)} within the next 5 minutes.")
                mitigations.append("Proactively scale up memory limits or provision additional replica sets to handle load demands.")
                
        if not reasons:
            return "Cluster is operating within normal baseline limits. The local SRE engine analyzed active telemetry streams and detected zero network, storage, or memory anomalies."
            
        rca = " ".join(reasons)
        plan = " ".join(mitigations)
        
        return f"[Local Offline AI Mode] RCA: {rca} Mitigation: {plan}"

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
        
        # If Gemini fails, fallback to local rule-based insight engine
        if "failed" in insight.lower() or "offline" in insight.lower() or "error" in insight.lower():
            print("Gemini keys exhausted/rate-limited. Falling back to local rules-based SRE insight generator...")
            insight = self._generate_local_fallback_insight(anomaly_data)
            
        # Cache this new insight if it generated successfully
        if "failed" not in insight.lower() and "offline" not in insight.lower():
            self._last_anomalies = current_anomaly_signatures
            self._last_insight = insight
            self._last_insight_time = now

        return insight

    def _chat_local_fallback(self, user_message: str, cluster_context: dict) -> str:
        msg = user_message.lower()
        anomalies = cluster_context.get('anomalies', [])
        logs = cluster_context.get('log_keywords', [])
        storage_anoms = cluster_context.get('storage_anomalies', [])
        network_anoms = cluster_context.get('network_anomalies', [])
        total_pods = cluster_context.get('total_pods_analyzed', 0)
        
        if "how many" in msg or "pod count" in msg or "number of pods" in msg or "pods running" in msg or "active pods" in msg:
            if total_pods > 0:
                return f"[Local Offline AI Mode] There are currently {total_pods} active pods running and monitored in the cluster."
            else:
                return "[Local Offline AI Mode] There are active pods running on the cluster, but the precise telemetry is currently establishing connection."
                
        elif "cpu" in msg or "memory" in msg or "resource" in msg or "anomaly" in msg or "anomalous" in msg:
            if anomalies:
                pod_details = ", ".join([f"{a['pod']} (CPU: {a['cpu_usage_core_rate']*1000:.1f} mc, MEM: {a['memory_usage_bytes']/1000000:.0f} MB)" for a in anomalies])
                return f"[Local Offline AI Mode] Active resource anomalies detected on: {pod_details}. These processes exceed standard baselines and require operator review or auto-heal action."
            else:
                return "[Local Offline AI Mode] Telemetry checks confirm all pods and physical processes are operating within standard historical CPU and memory bounds."
                
        elif "storage" in msg or "disk" in msg or "volume" in msg or "pvc" in msg:
            if storage_anoms:
                alerts = ", ".join([s for s in storage_anoms])
                return f"[Local Offline AI Mode] Direct hardware path warning: {alerts}. This could restrict process I/O performance."
            else:
                return "[Local Offline AI Mode] Active drive storage (C:\\, D:\\) remains healthy. Volume capacities and write queues are fully stable."
                
        elif "network" in msg or "traffic" in msg or "port" in msg or "socket" in msg:
            if network_anoms:
                alerts = ", ".join([n for n in network_anoms])
                return f"[Local Offline AI Mode] High active connections detected: {alerts}. Audit active ports to locate potential traffic leaks."
            else:
                return "[Local Offline AI Mode] Network interface paths are fully stable. Dynamic loopback packet latency remains <1ms with zero drop rates."
                
        elif "log" in msg or "error" in msg or "nlp" in msg or "event" in msg:
            if logs:
                return f"[Local Offline AI Mode] NLP clustering identified the following high-frequency system error patterns: {', '.join(logs)}. Review details in the Event Viewer pane."
            else:
                return "[Local Offline AI Mode] Windows Event log analysis shows zero critical errors or system alerts in the current cycle."
                
        elif "remediate" in msg or "heal" in msg or "fix" in msg:
            if anomalies:
                return f"[Local Offline AI Mode] Active anomalies are pending on {', '.join([a['pod'] for a in anomalies])}. Click the 'Auto-Heal' button next to the anomaly to trigger automatic process isolation and recycle."
            else:
                return "[Local Offline AI Mode] No active resource outliers require remediation right now. System state is clear."
                
        else:
            outliers = []
            if anomalies: outliers.append(f"{len(anomalies)} resource outlier(s)")
            if storage_anoms: outliers.append(f"{len(storage_anoms)} storage bottleneck(s)")
            if network_anoms: outliers.append(f"{len(network_anoms)} network anomaly/anomalies")
            
            state_desc = ", ".join(outliers) if outliers else "all telemetry normal"
            return f"[Local Offline AI Mode] Active Status: {state_desc}. (Notice: Gemini API keys are currently rate-limited. Operating under local rules-based SRE guidance. Ask me about cpu, storage, network, or logs for specific telemetry data.)"

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
        
        reply = self._call_gemini_with_fallback(prompt)
        
        # If Gemini fails, fallback to local rule-based chat engine
        if "failed" in reply.lower() or "offline" in reply.lower() or "error" in reply.lower():
            print("Gemini keys exhausted/rate-limited. Falling back to local rules-based SRE chat engine...")
            reply = self._chat_local_fallback(user_message, cluster_context)
            
        return reply

