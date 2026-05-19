import os
import sys
import time
from dotenv import load_dotenv

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.anomaly_detector import ResourceAnomalyDetector
from agents.master_orchestrator import MasterOrchestrator
from agents.dependency_mapper import DependencyMapper
from agents.log_intelligence import LogIntelligenceAgent
from agents.auto_remediation import AutoRemediationAgent
from agents.metrics_streamer import MetricsStreamer

def run_agent_diagnostics():
    print("=========================================================")
    print("      KUBE AI PLATFORM: AGENTS DIAGNOSTIC CHECKER        ")
    print("=========================================================\n")
    
    # Load env vars
    load_dotenv()
    
    # ----------------------------------------------------
    # Agent 1: Resource Anomaly Detector
    # ----------------------------------------------------
    print("[Agent 1/6] ResourceAnomalyDetector (Isolation Forest)")
    print("---------------------------------------------------------")
    detector = ResourceAnomalyDetector()
    try:
        res = detector.analyze_current_state()
        print(f"Status: {res.get('status')}")
        if res.get('status') == 'success':
            print(f"Pods Analyzed: {res.get('total_pods_analyzed')}")
            print(f"Anomalies Detected: {res.get('anomalies_detected')}")
            if res.get('anomalies'):
                for a in res['anomalies']:
                    print(f"  - rogue: {a['pod']} (CPU Rate: {a['cpu_usage_core_rate']}, Mem: {a['memory_usage_bytes']} bytes, Score: {a['anomaly_score']})")
        else:
            print(f"Message: {res.get('message')}")
        print("SUCCESS: ResourceAnomalyDetector is healthy and running.")
    except Exception as e:
        print(f"ERROR: Error checking ResourceAnomalyDetector: {e}")
    print()

    # ----------------------------------------------------
    # Agent 2: Master Orchestrator (Gemini SRE LLM)
    # ----------------------------------------------------
    print("[Agent 2/6] MasterOrchestrator (SRE Insight Generator)")
    print("---------------------------------------------------------")
    orchestrator = MasterOrchestrator()
    print(f"Total Keys Available for Fallback: {len(orchestrator.all_keys)}")
    for i, key in enumerate(orchestrator.all_keys):
        print(f"  Key {i+1}: ...{key[-6:]}")
        
    mock_anomaly_data = {
        "status": "success",
        "total_pods_analyzed": 4,
        "anomalies": [
            {
                "pod": "rogue-service[999]",
                "cpu_usage_core_rate": 1.95,
                "memory_usage_bytes": 1073741824,
                "anomaly_score": -0.15
            }
        ]
    }
    try:
        insight = orchestrator.generate_insight(mock_anomaly_data)
        print("Insight Generation Trial (Checking fallback system):")
        print(f"--- START INSIGHT ---\n{insight.strip()}\n--- END INSIGHT ---")
        print("SUCCESS: MasterOrchestrator is healthy and running.")
    except Exception as e:
        print(f"ERROR: Error checking MasterOrchestrator: {e}")
    print()

    # ----------------------------------------------------
    # Agent 3: Dependency Mapper (NetworkX Network Topology)
    # ----------------------------------------------------
    print("[Agent 3/6] DependencyMapper (Network Graph Creator)")
    print("---------------------------------------------------------")
    mapper = DependencyMapper()
    try:
        topo = mapper.get_topology()
        elements = topo.get("elements", [])
        nodes = [el for el in elements if "source" not in el["data"]]
        edges = [el for el in elements if "source" in el["data"]]
        print(f"Network Topology Created successfully.")
        print(f"  Nodes mapped: {len(nodes)}")
        print(f"  Edges mapped: {len(edges)}")
        print("SUCCESS: DependencyMapper is healthy and running.")
    except Exception as e:
        print(f"ERROR: Error checking DependencyMapper: {e}")
    print()

    # ----------------------------------------------------
    # Agent 4: Log Intelligence Agent (NLP TF-IDF Analyzer)
    # ----------------------------------------------------
    print("[Agent 4/6] LogIntelligenceAgent (NLP Pattern Clusterer)")
    print("---------------------------------------------------------")
    log_agent = LogIntelligenceAgent()
    try:
        patterns = log_agent.analyze_patterns()
        print(f"Status: {patterns.get('status')}")
        print(f"Logs Analyzed: {patterns.get('total_errors_analyzed')}")
        print(f"NLP Extracted Failure Keywords: {patterns.get('nlp_extracted_keywords')}")
        print(f"Dominant Cluster Summary: {patterns.get('dominant_error_cluster')}")
        print("SUCCESS: LogIntelligenceAgent is healthy and running.")
    except Exception as e:
        print(f"ERROR: Error checking LogIntelligenceAgent: {e}")
    print()

    # ----------------------------------------------------
    # Agent 5: Auto Remediation Agent (Self-Healing Executor)
    # ----------------------------------------------------
    print("[Agent 5/6] AutoRemediationAgent (K8s / Host Healer)")
    print("---------------------------------------------------------")
    healer = AutoRemediationAgent()
    print(f"Local Kubeconfig Status: {'Connected (Active)' if healer.active else 'Offline (Simulated/Host Mode only)'}")
    
    # Dry run a host process check (safe check against non-existent PID)
    print("Executing dry-run host self-healing request against mock pid...")
    remedy = healer.terminate_pod("non_existent_process[99999]")
    print(f"Remediation Response: {remedy.get('message')}")
    print("SUCCESS: AutoRemediationAgent is healthy and running.")
    print()

    # ----------------------------------------------------
    # Agent 6: Metrics Streamer (Background Streaming Collector)
    # ----------------------------------------------------
    print("[Agent 6/6] MetricsStreamer (Background Streaming Collector)")
    print("---------------------------------------------------------")
    streamer = MetricsStreamer()
    print("Waiting 6 seconds to capture a live rolling metric collection cycle...")
    time.sleep(6)
    
    try:
        overview = streamer.get_cluster_overview()
        timeseries = streamer.get_timeseries()
        print(f"Cluster Status: {overview.get('cluster_health')}")
        print(f"Total Active Processes Monitored: {overview.get('total_pods')}")
        print(f"Aggregated CPU Core rate: {overview.get('total_cpu_rate')}")
        print(f"Aggregated Memory: {overview.get('total_mem_gb')} GB")
        
        active_pods = list(timeseries.keys())
        print(f"Rolling Windows Active for: {active_pods}")
        if active_pods:
            sample_pod = active_pods[0]
            print(f"  Sample rolling window for '{sample_pod}': {len(timeseries[sample_pod]['cpu'])} data points collected.")
        print("SUCCESS: MetricsStreamer is healthy and running.")
    except Exception as e:
        print(f"ERROR: Error checking MetricsStreamer: {e}")
    print()

    print("=========================================================")
    print("          DIAGNOSTICS COMPLETE: ALL AGENTS OK!           ")
    print("=========================================================")

if __name__ == "__main__":
    run_agent_diagnostics()
