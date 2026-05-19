"""
SystemMetricsCollector
----------------------
Reads REAL live metrics from the host machine using psutil.
No Kubernetes or Prometheus required.
"""
import time
import psutil

# On first call, cpu_percent() returns 0 (initialises counters).
# We call it once at import time so subsequent calls return real values.
# List of common system processes to skip on Windows to avoid hangs/AccessDenied slowdowns
SYSTEM_PROCS = {
    "system idle process", "system", "registry", "smss.exe", "csrss.exe", 
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", 
    "fontdrvhost.exe", "svchost.exe", "dwm.exe", "memory compression",
    "lsaiso.exe", "wudfhost.exe", "spoolsv.exe", "nssm.exe",
    "vmmem", "vmmemwsl", "vmwp.exe"
}
_cpu_init_done = False

def _ensure_cpu_init():
    global _cpu_init_done
    if not _cpu_init_done:
        psutil.cpu_percent(interval=None)
        for p in psutil.process_iter():
            try:
                pid = p.pid
                if pid <= 4:
                    continue
                name = p.name()
                if name.lower() in SYSTEM_PROCS:
                    continue
                p.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _cpu_init_done = True


_ensure_cpu_init()


class SystemMetricsCollector:
    """Wraps psutil to expose process metrics in the same format
    used by PrometheusConnector, so all existing agents keep working."""

    TOP_N = 8   # How many top processes to track

    def get_top_processes_raw(self) -> list[dict]:
        """Return a list of dicts with name, cpu (0-100 %), and mem (bytes)."""
        procs = []
        for p in psutil.process_iter():
            try:
                pid = p.pid
                if pid <= 4:
                    continue
                name = p.name()
                if name.lower() in SYSTEM_PROCS:
                    continue
                
                # Fetch individually to avoid hangs in process_iter
                mem_info = p.memory_info()
                mem = mem_info.rss if mem_info else 0
                cpu = p.cpu_percent(interval=None) or 0.0
                
                procs.append({'name': f"{name}[{pid}]", 'cpu': cpu, 'mem': mem})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        procs.sort(key=lambda x: x['cpu'], reverse=True)
        return procs[: self.TOP_N]

    # ── Prometheus-compatible output ────────────────────────────────────────

    def get_pod_cpu_usage(self) -> list:
        """CPU as a fractional core rate (cpu_percent / 100)."""
        procs = self.get_top_processes_raw()
        now = time.time()
        return [
            {"metric": {"pod": p["name"]},
             "value": [now, str(round(p["cpu"] / 100.0, 6))]}
            for p in procs
        ]

    def get_pod_memory_usage(self) -> list:
        """Memory in bytes (RSS)."""
        procs = self.get_top_processes_raw()
        now = time.time()
        return [
            {"metric": {"pod": p["name"]},
             "value": [now, str(p["mem"])]}
            for p in procs
        ]

    # ── System-wide overview ────────────────────────────────────────────────

    def get_system_overview(self) -> dict:
        cpu_pct   = psutil.cpu_percent(interval=0.2)
        cpu_count = psutil.cpu_count(logical=True)
        mem       = psutil.virtual_memory()
        disk      = psutil.disk_usage('C:/')
        net       = psutil.net_io_counters()
        boot_ts   = psutil.boot_time()
        uptime_h  = round((time.time() - boot_ts) / 3600, 1)

        return {
            "cpu_percent":      cpu_pct,
            "cpu_count":        cpu_count,
            "mem_total_gb":     round(mem.total / 1e9, 2),
            "mem_used_gb":      round(mem.used  / 1e9, 2),
            "mem_percent":      mem.percent,
            "disk_total_gb":    round(disk.total / 1e9, 1),
            "disk_used_gb":     round(disk.used  / 1e9, 1),
            "disk_percent":     disk.percent,
            "net_sent_mb":      round(net.bytes_sent / 1e6, 1),
            "net_recv_mb":      round(net.bytes_recv / 1e6, 1),
            "uptime_hours":     uptime_h,
        }

    def get_full_process_list(self, top: int = 20) -> list[dict]:
        """Full sorted process list for the process table panel."""
        procs = []
        for p in psutil.process_iter():
            try:
                pid = p.pid
                if pid <= 4:
                    continue
                name = p.name()
                if name.lower() in SYSTEM_PROCS:
                    continue
                
                status = p.status()
                cpu = p.cpu_percent(interval=None) or 0.0
                mem_info = p.memory_info()
                mem = mem_info.rss if mem_info else 0
                
                try:
                    user = p.username()
                except Exception:
                    user = ''
                
                procs.append({
                    "pid":      pid,
                    "name":     name,
                    "status":   status,
                    "cpu_pct":  round(cpu, 2),
                    "mem_mb":   round(mem / 1e6, 1),
                    "user":     user.split('\\')[-1],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        procs.sort(key=lambda x: x['cpu_pct'], reverse=True)
        return procs[:top]
