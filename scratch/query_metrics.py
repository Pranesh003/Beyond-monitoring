import requests

base_url = "http://localhost:30000"

def query(q):
    r = requests.get(f"{base_url}/api/v1/query", params={"query": q})
    print(f"--- QUERY: {q} ---")
    if r.status_code == 200:
        data = r.json()
        results = data.get("data", {}).get("result", [])
        print(f"Results count: {len(results)}")
        for item in results[:10]:
            print(f"Metric: {item.get('metric')}, Value: {item.get('value')}")
    else:
        print(f"Error: {r.status_code}, {r.text}")

# Query basic container memory usage
query("container_memory_usage_bytes")
# Query cpu usage
query("container_cpu_usage_seconds_total")
# Query targets/up
query("up")
