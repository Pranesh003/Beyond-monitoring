from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agents.anomaly_detector import ResourceAnomalyDetector
from agents.master_orchestrator import MasterOrchestrator
from agents.dependency_mapper import DependencyMapper
from agents.log_intelligence import LogIntelligenceAgent
from agents.auto_remediation import AutoRemediationAgent
from agents.metrics_streamer import MetricsStreamer
from agents.storage_agent import StorageIntelligenceAgent
from agents.network_agent import NetworkIntelligenceAgent
from agents.forecasting_agent import ForecastingAgent

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
storage_agent = StorageIntelligenceAgent()
network_agent = NetworkIntelligenceAgent()
forecasting_agent = ForecastingAgent()

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
    return {
        "status": "healthy", 
        "components": {
            "database": "ok", 
            "ai_agents": "ok",
            "storage_intelligence": "active",
            "network_intelligence": "active",
            "forecasting_intelligence": "active"
        }
    }

@app.get("/api/v1/anomalies")
def get_anomalies():
    detection_result = anomaly_detector.analyze_current_state()
    
    # Enrich detection result with storage, network, and forecasting predictions
    storage_state = storage_agent.monitor_storage()
    storage_anoms = storage_agent.detect_bottlenecks()
    network_anoms = network_agent.detect_network_anomalies()
    
    timeseries = metrics_streamer.get_timeseries()
    forecasts = forecasting_agent.forecast_pod_metrics(timeseries)
    pvc_tte = forecasting_agent.calculate_time_to_exhaustion(storage_state)
    
    predictions = forecasting_agent.predict_failures(forecasts, detection_result.get("anomalies", []), network_anoms, storage_anoms)
    scaling_reqs = forecasting_agent.estimate_scaling_requirements(predictions)
    storage_correlations = storage_agent.correlate_pvc_failures([a["pod"] for a in detection_result.get("anomalies", [])])

    detection_result["storage_anomalies"] = storage_anoms
    detection_result["network_anomalies"] = network_anoms
    detection_result["predictions"] = predictions
    detection_result["scaling_requirements"] = scaling_reqs
    detection_result["storage_correlations"] = storage_correlations
    
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

@app.get("/api/v1/storage")
def get_storage():
    state = storage_agent.monitor_storage()
    bottlenecks = storage_agent.detect_bottlenecks()
    return {
        "status": "success",
        "storage_state": state,
        "bottlenecks": bottlenecks
    }

@app.get("/api/v1/network")
def get_network():
    state = network_agent.analyze_network_state()
    anomalies = network_agent.detect_network_anomalies()
    return {
        "status": "success",
        "network_state": state,
        "anomalies": anomalies
    }

@app.get("/api/v1/forecasts")
def get_forecasts():
    timeseries = metrics_streamer.get_timeseries()
    storage_state = storage_agent.monitor_storage()
    
    forecasts = forecasting_agent.forecast_pod_metrics(timeseries)
    pvc_tte = forecasting_agent.calculate_time_to_exhaustion(storage_state)
    
    anom_result = anomaly_detector.analyze_current_state()
    storage_anoms = storage_agent.detect_bottlenecks()
    network_anoms = network_agent.detect_network_anomalies()
    
    predictions = forecasting_agent.predict_failures(forecasts, anom_result.get("anomalies", []), network_anoms, storage_anoms)
    scaling_reqs = forecasting_agent.estimate_scaling_requirements(predictions)

    return {
        "status": "success",
        "resource_forecasts": forecasts,
        "storage_time_to_exhaustion": pvc_tte,
        "failure_predictions": predictions,
        "recommended_scaling": scaling_reqs
    }

@app.post("/api/v1/chat")
def chat_endpoint(request: ChatRequest):
    anom_result = anomaly_detector.analyze_current_state()
    log_result = log_agent.analyze_patterns()
    storage_anoms = storage_agent.detect_bottlenecks()
    network_anoms = network_agent.detect_network_anomalies()
    
    context = {
        "anomalies": anom_result.get("anomalies", []),
        "log_keywords": log_result.get("nlp_extracted_keywords", []),
        "storage_anomalies": [s["message"] for s in storage_anoms],
        "network_anomalies": [n["message"] for n in network_anoms]
    }
    
    answer = master_orchestrator.chat_with_assistant(request.message, context)
    return {"reply": answer}

@app.post("/api/v1/remediate")
def remediate_pod(request: RemediationRequest):
    return remediation_agent.terminate_pod(request.pod_name, request.namespace)

@app.get("/api/v1/metrics/timeseries")
def get_timeseries():
    return metrics_streamer.get_timeseries()

@app.get("/api/v1/cluster/overview")
def get_cluster_overview():
    return metrics_streamer.get_cluster_overview()
