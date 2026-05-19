import psutil
import time

print("Starting robust process iteration...")
t0 = time.time()
procs = []

# List of common system processes to skip on Windows to avoid hangs/AccessDenied slowdowns
SYSTEM_PROCS = {
    "system idle process", "system", "registry", "smss.exe", "csrss.exe", 
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", 
    "fontdrvhost.exe", "svchost.exe", "dwm.exe", "memory compression",
    "lsaiso.exe", "wudfhost.exe", "spoolsv.exe", "nssm.exe",
    "vmmem", "vmmemwsl", "vmwp.exe"
}

for p in psutil.process_iter():
    try:
        pid = p.pid
        if pid <= 4:
            continue
            
        name = p.name()
        if name.lower() in SYSTEM_PROCS:
            continue
            
        # Access memory info individually
        mem_info = p.memory_info()
        mem = mem_info.rss if mem_info else 0
        
        cpu = p.cpu_percent(interval=None) or 0.0
        
        procs.append({
            "pid": pid,
            "name": f"{name}[{pid}]",
            "cpu": cpu,
            "mem": mem
        })
        print(f"Success: {name}[{pid}] - CPU {cpu} - MEM {mem}")
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"Skipped {p.pid} due to: {type(e).__name__}")
    except Exception as e:
        print(f"Error {p.pid}: {e}")

print(f"Done in {time.time() - t0:.2f} seconds. Found {len(procs)} processes.")
