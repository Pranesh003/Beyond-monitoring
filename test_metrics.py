import sys
import time
print("Importing psutil...")
import psutil
print("Psutil imported.")

print("Iterating processes...")
t0 = time.time()
for p in psutil.process_iter():
    try:
        # Just print name to see progress
        name = p.name()
        cpu = p.cpu_percent(interval=None)
        print(f"Process {p.pid}: {name} -> {cpu}")
    except Exception as e:
        print(f"Error for {p.pid}: {e}")
print(f"Done in {time.time() - t0:.2f} seconds")
