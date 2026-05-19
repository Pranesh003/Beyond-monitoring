import os
import sys
from dotenv import load_dotenv

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.master_orchestrator import MasterOrchestrator

def main():
    print("=== Testing Resilient Gemini API Key Fallback and Rotation ===")
    
    # Instantiate MasterOrchestrator
    orchestrator = MasterOrchestrator()
    
    print("\n--- Listing Configured Keys ---")
    print(f"Total keys configured: {len(orchestrator.all_keys)}")
    for idx, key in enumerate(orchestrator.all_keys):
        print(f"Key {idx + 1}: ...{key[-6:]}")
        
    print("\n--- 1. Testing Normal Insight Generation ---")
    test_anomaly_data = {
        "status": "success",
        "total_pods_analyzed": 5,
        "anomalies": []
    }
    
    insight = orchestrator.generate_insight(test_anomaly_data)
    print(f"Resulting Insight:\n{insight}\n")
    
    print("\n--- 2. Simulating Corrupt Key and Fallback Rotation ---")
    # We will prepending an invalid key at the start of all_keys to simulate a failure
    orchestrator.all_keys.insert(0, "INVALID_MOCK_GOOGLE_KEY_FOR_TESTING")
    orchestrator.current_key_index = 0
    # Reset model to force configuration with the invalid key
    orchestrator.model = None
    
    print("Created mock invalid key as primary. Triggering insight generation...")
    insight_fallback = orchestrator.generate_insight(test_anomaly_data)
    print(f"\nResulting Insight with Fallback:\n{insight_fallback}\n")
    
    # Check if current_key_index has advanced to the next valid key
    print(f"Current key index after fallback: {orchestrator.current_key_index}")
    active_key = orchestrator.all_keys[orchestrator.current_key_index]
    print(f"Active key ends with: ...{active_key[-6:]}")
    
    if "failed" in insight_fallback.lower():
        print("TEST FAILED: Fallback did not succeed.")
    else:
        print("TEST SUCCESS: Fallback rotated keys successfully and completed generation!")

if __name__ == "__main__":
    main()
