import os
import psutil
import time

class StorageIntelligenceAgent:
    """
    Storage & PVC Intelligence Agent
    --------------------------------
    - Monitors physical disk capacity and partition utilization of the host machine.
    - Tracks disk read/write operations (actual IOPS & physical hardware latency).
    - Detects storage bottlenecks (utilization thresholds, elevated hardware latency).
    - Correlates physical drive stress with high resource process failures.
    """
    def __init__(self):
        self.default_disk_path = '/' if os.name != 'nt' else 'C:/'
        # State memory to compute real-time delta IOPS and physical IO latency
        self._prev_io = {} # mountpoint -> {timestamp, read_count, write_count, read_bytes, write_bytes, read_time, write_time}

    def monitor_storage(self) -> dict:
        """
        Gathers raw capacity and IO statistics from actual local physical drives
        and structures them as active system PVCs.
        """
        now = time.time()
        
        # 1. Gather overall host IO counters
        try:
            io = psutil.disk_io_counters()
            host_io = {
                "read_count": io.read_count if io else 0,
                "write_count": io.write_count if io else 0,
                "read_bytes_mb": round((io.read_bytes / 1e6) if io else 0.0, 2),
                "write_bytes_mb": round((io.write_bytes / 1e6) if io else 0.0, 2),
            }
        except Exception:
            host_io = {"read_count": 0, "write_count": 0, "read_bytes_mb": 0.0, "write_bytes_mb": 0.0}

        # 2. Query all physical mounted partitions
        pvcs_mapped = []
        partitions = []
        try:
            for p in psutil.disk_partitions(all=False):
                if not p.mountpoint:
                    continue
                # Skip optical CD-ROMs
                if os.name == 'nt' and 'cdrom' in p.opts.lower():
                    continue
                partitions.append(p)
        except Exception:
            # Fallback to default disk partition if enumeration fails
            class FallbackPartition:
                mountpoint = self.default_disk_path
                device = 'PrimaryDrive'
                opts = 'rw'
            partitions = [FallbackPartition()]

        # Get per-drive IO counters
        perdisk_io = {}
        try:
            perdisk_io = psutil.disk_io_counters(perdisk=True)
        except Exception:
            pass

        for partition in partitions:
            m = partition.mountpoint
            try:
                usage = psutil.disk_usage(m)
            except Exception:
                continue # Access denied or empty media (like floppy or disconnected network drive)

            # Match partition with its physical disk device IO counters
            matching_io = None
            clean_mount = m.replace('\\', '').replace('/', '').replace(':', '').upper()
            for key, val in perdisk_io.items():
                if clean_mount in key.upper() or key.upper() in clean_mount:
                    matching_io = val
                    break
            
            # Fallback to global counters if partition-specific is missing
            if not matching_io and len(perdisk_io) > 0:
                matching_io = list(perdisk_io.values())[0]
            elif not matching_io:
                # Mock a counter class if disk_io_counters is completely disabled on the system
                class DummyIO:
                    read_count = 0
                    write_count = 0
                    read_bytes = 0
                    write_bytes = 0
                    read_time = 0
                    write_time = 0
                matching_io = DummyIO()

            # Retrieve previous state to calculate delta IOPS and Latency
            prev = self._prev_io.get(m)
            
            # Initial defaults
            iops_read = 0.0
            iops_write = 0.0
            read_latency_ms = 0.0
            write_latency_ms = 0.0

            if prev:
                elapsed = now - prev["timestamp"]
                if elapsed > 0.1:
                    delta_reads = max(0, matching_io.read_count - prev["read_count"])
                    delta_writes = max(0, matching_io.write_count - prev["write_count"])
                    
                    iops_read = round(delta_reads / elapsed, 1)
                    iops_write = round(delta_writes / elapsed, 1)
                    
                    # Calculate physical hardware latency spent on reads/writes
                    # read_time and write_time are in milliseconds
                    if hasattr(matching_io, 'read_time') and hasattr(matching_io, 'write_time'):
                        delta_read_time = max(0, matching_io.read_time - prev["read_time"])
                        delta_write_time = max(0, matching_io.write_time - prev["write_time"])
                        
                        read_latency_ms = round(delta_read_time / delta_reads, 2) if delta_reads > 0 else 0.0
                        write_latency_ms = round(delta_write_time / delta_writes, 2) if delta_writes > 0 else 0.0

            # Store state for next poll
            self._prev_io[m] = {
                "timestamp": now,
                "read_count": matching_io.read_count,
                "write_count": matching_io.write_count,
                "read_bytes": matching_io.read_bytes,
                "write_bytes": matching_io.write_bytes,
                "read_time": getattr(matching_io, 'read_time', 0),
                "write_time": getattr(matching_io, 'write_time', 0)
            }

            pvc_name = f"pvc-{clean_mount.lower() or 'root'}"
            volume_name = f"{clean_mount.lower() or 'root'}-storage"
            
            capacity_gb = round(usage.total / 1e9, 2)
            used_gb = round(usage.used / 1e9, 2)
            percent = usage.percent

            pvcs_mapped.append({
                "pvc_name": pvc_name,
                "volume_name": volume_name,
                "target_pod": f"local-drive-{clean_mount or 'system'}",
                "capacity_gb": capacity_gb,
                "used_gb": used_gb,
                "percent_used": percent,
                "iops_read": iops_read,
                "iops_write": iops_write,
                "read_latency_ms": read_latency_ms,
                "write_latency_ms": write_latency_ms,
                "status": "warning" if percent > 90.0 or write_latency_ms > 100.0 else "healthy"
            })

        # Main system disk for the generic host_disk key
        try:
            main_usage = psutil.disk_usage(self.default_disk_path)
            host_disk = {
                "path": self.default_disk_path,
                "total_gb": round(main_usage.total / 1e9, 2),
                "used_gb": round(main_usage.used / 1e9, 2),
                "free_gb": round(main_usage.free / 1e9, 2),
                "percent_used": main_usage.percent
            }
        except Exception as e:
            host_disk = {"error": f"Failed to retrieve host storage: {e}"}

        return {
            "host_disk": host_disk,
            "host_io_counters": host_io,
            "persistent_volume_claims": pvcs_mapped,
            "timestamp": now
        }

    def detect_bottlenecks(self) -> list[dict]:
        """
        Analyzes live physical storage metrics to identify capacity and performance issues.
        """
        metrics = self.monitor_storage()
        bottlenecks = []

        # Check partitions / virtual PVCs
        for pvc in metrics.get("persistent_volume_claims", []):
            if pvc["percent_used"] > 95.0:
                bottlenecks.append({
                    "entity": pvc["pvc_name"],
                    "type": "pvc_exhaustion",
                    "severity": "critical",
                    "message": f"Physical partition {pvc['pvc_name'].replace('pvc-', '').upper()} is critically low on space ({pvc['percent_used']}%)."
                })
            elif pvc["percent_used"] > 88.0:
                bottlenecks.append({
                    "entity": pvc["pvc_name"],
                    "type": "pvc_near_exhaustion",
                    "severity": "warning",
                    "message": f"Physical partition {pvc['pvc_name'].replace('pvc-', '').upper()} has exceeded 88% capacity limit."
                })

            if pvc["write_latency_ms"] > 100.0:
                bottlenecks.append({
                    "entity": pvc["pvc_name"],
                    "type": "io_saturation",
                    "severity": "critical",
                    "message": f"Physical partition {pvc['pvc_name'].replace('pvc-', '').upper()} is suffering from severe write latency ({pvc['write_latency_ms']} ms)."
                })

        return bottlenecks

    def correlate_pvc_failures(self, anomalous_pods: list[str]) -> list[dict]:
        """
        Correlates live storage bottlenecks with active anomalous processes.
        """
        bottlenecks = self.detect_bottlenecks()
        correlations = []

        for p_name in anomalous_pods:
            for b in bottlenecks:
                correlations.append({
                    "pod": p_name,
                    "pvc": b["entity"],
                    "root_cause_factor": b["type"],
                    "severity": b["severity"],
                    "analysis": f"The process resource abnormality in '{p_name}' correlates with high '{b['type']}' storage alert on partition volume {b['entity']}. Detail: {b['message']}"
                })

        return correlations
