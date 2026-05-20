import requests

base_url = "http://localhost:30000"

def query(q):
    r = requests.get(f"{base_url}/api/v1/query", params={"query": q})
    print(f"--- QUERY: {q} ---")
    if r.status_code == 200:
        data = r.json()
        results = data.get("data", {}).get("result", [])
        print(f"Results count: {len(results)}")
        for item in results:
            metric = item.get('metric')
            if 'pod' in metric or 'pod_name' in metric or 'container' in metric or 'namespace' in metric:
                print("Found match:", metric)
            elif any('test-apps' in str(v) for v in metric.values()):
                print("Found test-apps match:", metric)
    else:
        print(f"Error: {r.status_code}, {r.text}")

query("container_memory_usage_bytes")
