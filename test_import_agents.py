import sys
import time

def log(msg):
    print(msg)
    sys.stdout.flush()

log("1. Importing psutil...")
import psutil

log("2. Importing sklearn.ensemble...")
from sklearn.ensemble import IsolationForest

log("3. Importing sklearn.feature_extraction.text...")
from sklearn.feature_extraction.text import TfidfVectorizer

log("4. Importing networkx...")
import networkx as nx

log("5. Importing google.generativeai...")
import google.generativeai as genai

log("6. Importing kubernetes...")
from kubernetes import client, config

log("7. Loading kubeconfig...")
try:
    config.load_kube_config()
    log("Kubeconfig loaded.")
except Exception as e:
    log(f"Kubeconfig error: {e}")

log("8. Importing agents.system_metrics...")
from backend.agents.system_metrics import SystemMetricsCollector

log("9. Instantiating SystemMetricsCollector...")
collector = SystemMetricsCollector()
log("SystemMetricsCollector instantiated.")

log("10. Fetching processes...")
procs = collector.get_top_processes_raw()
log(f"Processes fetched: {len(procs)}")

log("11. Importing agents.prometheus_client...")
from backend.agents.prometheus_client import PrometheusConnector

log("12. Instantiating PrometheusConnector...")
prom = PrometheusConnector()
log("PrometheusConnector instantiated.")

log("13. Getting cpu usage...")
cpu = prom.get_pod_cpu_usage()
log(f"CPU usage: {len(cpu)}")

log("All tests passed!")
