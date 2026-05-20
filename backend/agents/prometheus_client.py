"""
PrometheusConnector
-------------------
Tries to reach a real Prometheus instance first.
Falls back to LIVE psutil system metrics (not fake mock data).
"""
import os
import socket
from .system_metrics import SystemMetricsCollector

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:30000")

_sys = SystemMetricsCollector()   # singleton


class PrometheusConnector:
    def __init__(self, base_url: str = PROMETHEUS_URL):
        self.base_url = base_url
        self._prom = None
        self.is_up = self._probe_prometheus()
        if self.is_up:
            try:
                from prometheus_api_client import PrometheusConnect
                self._prom = PrometheusConnect(url=base_url, disable_ssl=True)
            except Exception:
                pass

    def _probe_prometheus(self) -> bool:
        try:
            parts = self.base_url.replace("http://", "").replace("https://", "").split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 80
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except Exception:
            return False

    # ── public interface (same as before) ──────────────────────────────────

    def get_pod_cpu_usage(self) -> list:
        if self.is_up and self._prom:
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
        if self.is_up and self._prom:
            query = ('sum(container_memory_usage_bytes'
                     '{namespace="test-apps",container!=""}) by (pod)')
            try:
                res = self._prom.custom_query(query)
                if res:
                    return res
            except Exception:
                pass

        return _sys.get_pod_memory_usage()
