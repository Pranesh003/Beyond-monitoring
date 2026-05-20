import requests

base_url = "http://localhost:30000"

r = requests.get(f"{base_url}/api/v1/query", params={"query": "container_memory_usage_bytes"})
if r.status_code == 200:
    results = r.json().get("data", {}).get("result", [])
    print(f"Results: {len(results)}")
    for item in results[:20]:
        print(item.get("metric"))
else:
    print("Error:", r.text)
