import sys
import os
from dotenv import load_dotenv

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.master_orchestrator import MasterOrchestrator

def main():
    print("=== Testing Local Offline Heuristic SRE Insights and Chat ===")
    
    orchestrator = MasterOrchestrator()
    
    # Prepend invalid key at the start of all_keys and clear model to force API failures
    orchestrator.all_keys = ["INVALID_MOCK_GOOGLE_KEY_FOR_TESTING"]
    orchestrator.current_key_index = 0
    orchestrator.model = None
    
    # Create active anomalies to bypass the normal static optimization
    test_anomaly_data = {
        "status": "success",
        "total_pods_analyzed": 8,
        "anomalies": [
            {
                "pod": "rogue-pod",
                "cpu_usage_core_rate": 0.95,
                "memory_usage_bytes": 850000000,
                "agent_reasoning": "Memory spike on rogue-pod"
            }
        ],
        "storage_anomalies": [
            {
                "entity": "C:\\",
                "message": "Queue length exceeded limits",
                "type": "I/O Latency",
                "severity": "Warning"
            }
        ],
        "network_anomalies": [
            {
                "flow": "api-gateway -> rogue-pod (Port 8080)",
                "message": "High packet drop rates detected"
            }
        ],
        "predictions": [
            {
                "pod": "rogue-pod",
                "failure_probability": 0.88,
                "leading_indicators": ["Memory Leak", "I/O Block"]
            }
        ],
        "scaling_requirements": [
            {
                "action_details": "Scale memory limit on rogue-pod"
            }
        ],
        "storage_correlations": []
    }
    
    print("\n--- Triggering Insight Generation (with forced API failure) ---")
    insight = orchestrator.generate_insight(test_anomaly_data)
    print(f"Resulting Insight:\n{insight}\n")
    
    print("\n--- Triggering Chat Assistant Query (with forced API failure) ---")
    context = {
        "anomalies": test_anomaly_data["anomalies"],
        "log_keywords": ["NullPointerException", "OutOfMemoryError"],
        "storage_anomalies": ["C:\\ Queue length exceeded limits"],
        "network_anomalies": ["api-gateway -> rogue-pod (Port 8080) High packet drop"]
    }
    
    reply = orchestrator.chat_with_assistant("What active resource anomalies and storage bottlenecks exist?", context)
    print(f"Resulting Chat Reply:\n{reply}\n")
    
    reply_generic = orchestrator.chat_with_assistant("What is the general status?", context)
    print(f"Resulting Chat Reply (Generic Query):\n{reply_generic}\n")
    
    if "[Local Offline AI Mode]" in insight and "[Local Offline AI Mode]" in reply:
        print("TEST SUCCESS: Both SRE Insight and Chat fallback to the offline rule engines successfully!")
    else:
        print("TEST FAILED: Fallback was not activated properly.")

if __name__ == "__main__":
    main()
