"""
MetricsStreamer Agent
---------------------
Maintains a rolling in-memory time-series store for per-pod CPU & memory metrics.
Produces realistic fluctuating data based on real Prometheus values or falls
back to a simulation that models the rogue-pod spike pattern.
"""
import time
import random
import threading
from collections import deque
from .prometheus_client import PrometheusConnector

# Number of data-points kept in each rolling window (30 × 5s = 2.5 min window)
WINDOW_SIZE = 30

class MetricsStreamer:
    def __init__(self):
        self.prom_client = PrometheusConnector()
        # { pod_name: { "cpu": deque([…]), "mem": deque([…]), "timestamps": deque([…]) } }
        self._store: dict = {}
        self._lock = threading.Lock()
        
        # Background thread to keep the window rolling
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_loop(self):
        while True:
            time.sleep(5)
            self._tick()

    def _tick(self):
        """Pull fresh values from Prometheus (or system) and append to deques."""
        cpu_raw = self.prom_client.get_pod_cpu_usage()
        mem_raw = self.prom_client.get_pod_memory_usage()

        cpu_map = {item["metric"].get("pod", "unknown"): float(item["value"][1]) for item in cpu_raw}
        mem_map = {item["metric"].get("pod", "unknown"): float(item["value"][1]) for item in mem_raw}

        now = time.time()
        with self._lock:
            current_pods = set(cpu_map.keys()) | set(mem_map.keys())
            
            for pod in current_pods:
                entry = self._store.setdefault(pod, {
                    "timestamps": deque(maxlen=WINDOW_SIZE),
                    "cpu": deque(maxlen=WINDOW_SIZE),
                    "mem": deque(maxlen=WINDOW_SIZE),
                })
                entry["timestamps"].append(now)
                entry["cpu"].append(max(0.0, cpu_map.get(pod, 0.0)))
                entry["mem"].append(max(0.0, mem_map.get(pod, 0.0)))
                
            # Prune pods that are no longer active
            pods_to_remove = [p for p in self._store if p not in current_pods]
            for p in pods_to_remove:
                del self._store[p]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_timeseries(self) -> dict:
        """Return the full rolling window for all pods, formatted for Chart.js."""
        with self._lock:
            result = {}
            for pod, data in self._store.items():
                result[pod] = {
                    "timestamps": [round(t * 1000) for t in data["timestamps"]],  # ms epoch
                    "cpu":  [round(v, 6) for v in data["cpu"]],
                    "mem":  [round(v, 0) for v in data["mem"]],
                }
        return result

    def get_cluster_overview(self) -> dict:
        """
        Returns aggregated cluster-level statistics for the KPI header cards.
        """
        with self._lock:
            pod_stats = []
            total_cpu = 0.0
            total_mem = 0.0
            for pod, data in self._store.items():
                last_cpu = data["cpu"][-1] if data["cpu"] else 0
                last_mem = data["mem"][-1] if data["mem"] else 0
                # Trend: last value vs average of the previous 5
                window = list(data["cpu"])
                trend_cpu = "up" if len(window) >= 6 and window[-1] > (sum(window[-6:-1]) / 5) else "stable"
                pod_stats.append({
                    "pod":      pod,
                    "cpu":      round(last_cpu, 6),
                    "mem_mb":   round(last_mem / 1_000_000, 1),
                    "trend":    trend_cpu,
                })
                total_cpu += last_cpu
                total_mem += last_mem

        return {
            "total_pods":       len(pod_stats),
            "total_cpu_rate":   round(total_cpu, 5),
            "total_mem_gb":     round(total_mem / 1_000_000_000, 2),
            "pods":             pod_stats,
            "cluster_health":   "warning" if any(p["pod"] == "rogue-pod" for p in pod_stats) else "healthy",
        }
