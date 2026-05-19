from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agents.anomaly_detector import ResourceAnomalyDetector
from agents.master_orchestrator import MasterOrchestrator
from agents.dependency_mapper import DependencyMapper
from agents.log_intelligence import LogIntelligenceAgent
from agents.auto_remediation import AutoRemediationAgent
from agents.metrics_streamer import MetricsStreamer

app = FastAPI(
    title="Kube AI Master Orchestrator",
    description="Agentic AI-powered Kubernetes Intelligence and Resource Correlation Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI Agents
anomaly_detector = ResourceAnomalyDetector()
master_orchestrator = MasterOrchestrator()
dependency_mapper = DependencyMapper()
log_agent = LogIntelligenceAgent()
remediation_agent = AutoRemediationAgent()
metrics_streamer = MetricsStreamer()   # Starts background collection thread

class ChatRequest(BaseModel):
    message: str

class RemediationRequest(BaseModel):
    pod_name: str
    namespace: str = "test-apps"

@app.get("/")
def read_root():
    return {"message": "Welcome to the Agentic AI Kubernetes Intelligence Platform API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "components": {"database": "ok", "ai_agents": "ok"}}

@app.get("/api/v1/anomalies")
def get_anomalies():
    detection_result = anomaly_detector.analyze_current_state()
    if detection_result.get("status") == "success":
        insight = master_orchestrator.generate_insight(detection_result)
        detection_result["master_insight"] = insight
    else:
        detection_result["master_insight"] = "Unable to generate insight due to missing telemetry data."
    return detection_result

@app.get("/api/v1/topology")
def get_topology():
    return dependency_mapper.get_topology()

@app.get("/api/v1/logs/analysis")
def get_log_analysis():
    return log_agent.analyze_patterns()

@app.post("/api/v1/chat")
def chat_endpoint(request: ChatRequest):
    anom_result = anomaly_detector.analyze_current_state()
    log_result = log_agent.analyze_patterns()
    
    context = {
        "anomalies": anom_result.get("anomalies", []),
        "log_keywords": log_result.get("nlp_extracted_keywords", [])
    }
    
    answer = master_orchestrator.chat_with_assistant(request.message, context)
    return {"reply": answer}

@app.post("/api/v1/remediate")
def remediate_pod(request: RemediationRequest):
    """
    Triggers the Auto-Remediation agent to self-heal the cluster by terminating 
    anomalous pods, allowing Kubernetes to automatically restart fresh replicas.
    """
    return remediation_agent.terminate_pod(request.pod_name, request.namespace)

@app.get("/api/v1/metrics/timeseries")
def get_timeseries():
    """
    Returns a rolling 30-point, 2.5-minute time-series window for every pod.
    Refreshed every 5 seconds by a background collection thread.
    """
    return metrics_streamer.get_timeseries()

@app.get("/api/v1/cluster/overview")
def get_cluster_overview():
    """
    Returns aggregated cluster-level KPIs: total CPU rate, memory, per-pod trends.
    """
    return metrics_streamer.get_cluster_overview()
