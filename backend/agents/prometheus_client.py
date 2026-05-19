"""
PrometheusConnector
-------------------
Tries to reach a real Prometheus instance first.
Falls back to LIVE psutil system metrics (not fake mock data).
"""
import os
from .system_metrics import SystemMetricsCollector

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:30000")

_sys = SystemMetricsCollector()   # singleton


class PrometheusConnector:
    def __init__(self, base_url: str = PROMETHEUS_URL):
        self.base_url = base_url
        self._prom = None
        try:
            from prometheus_api_client import PrometheusConnect
            self._prom = PrometheusConnect(url=base_url, disable_ssl=True)
        except Exception:
            pass

    # ── public interface (same as before) ──────────────────────────────────

    def get_pod_cpu_usage(self) -> list:
        if self._prom:
            query = ('sum(rate(container_cpu_usage_seconds_total'
                     '{namespace="test-apps",container!=""}[2m])) by (pod)')
            try:
                res = self._prom.custom_query(query)
                if res:
                    return res
            except Exception as e:
                print(f"Prometheus unreachable: {e}. Using live system data.")

        # ── Real live data from this machine ──────────────────────────────
        return _sys.get_pod_cpu_usage()

    def get_pod_memory_usage(self) -> list:
        if self._prom:
            query = ('sum(container_memory_usage_bytes'
                     '{namespace="test-apps",container!=""}) by (pod)')
            try:
                res = self._prom.custom_query(query)
                if res:
                    return res
            except Exception:
                pass

        return _sys.get_pod_memory_usage()
