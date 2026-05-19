import numpy as np
import time

class ForecastingAgent:
    """
    Forecasting & Prediction Agent
    ------------------------------
    - Fits linear regression curves to rolling telemetry to forecast CPU & RAM usage.
    - Estimates Time-to-Exhaustion (TTE) for physical partitions and RAM boundaries.
    - Computes a mathematical process/pod failure probability index based on live resources.
    - Details elastic scaling recommendations for handling local process/container contention.
    """
    def __init__(self):
        # Sliding history window of partition usage to calculate actual live filling rate
        self._storage_history = {} # pvc_name -> list of used_gb values

    def _fit_linear_projection(self, history: list[float], steps_ahead: int) -> float:
        """
        Fits a simple linear least-squares regression line (y = mx + c)
        over the historical data array, projecting y at x = len(history) + steps_ahead.
        """
        n = len(history)
        if n < 5:
            # Not enough history to fit a curve, return the last known value
            return history[-1] if history else 0.0

        x = np.arange(n)
        y = np.array(history)

        # Calculate slope (m) and intercept (c)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return history[-1]

        slope = numerator / denominator
        intercept = y_mean - (slope * x_mean)

        projected_x = n + steps_ahead
        projected_y = (slope * projected_x) + intercept

        return projected_y

    def forecast_pod_metrics(self, rolling_timeseries: dict) -> dict:
        """
        Iterates over rolling per-pod/process historical measurements,
        forecasting resource utilization 1 minute (12 ticks) and 5 minutes (60 ticks) ahead.
        """
        forecasts = {}
        for pod_name, metrics in rolling_timeseries.items():
            cpu_history = metrics.get("cpu", [])
            mem_history = metrics.get("mem", [])

            # Project 1 minute (12 ticks of 5s) & 5 minutes (60 ticks of 5s)
            cpu_1m = max(0.0, self._fit_linear_projection(cpu_history, 12))
            cpu_5m = max(0.0, self._fit_linear_projection(cpu_history, 60))

            # Limit projected CPU to 1.0 (100% core load)
            cpu_1m = min(1.0, cpu_1m)
            cpu_5m = min(1.0, cpu_5m)

            mem_1m = max(0.0, self._fit_linear_projection(mem_history, 12))
            mem_5m = max(0.0, self._fit_linear_projection(mem_history, 60))

            # Determine Memory Leak Trajectory (slope check)
            leak_detected = False
            if len(mem_history) >= 10:
                mem_arr = np.array(mem_history)
                slope = np.polyfit(np.arange(len(mem_arr)), mem_arr, 1)[0]
                # If memory slope is strictly positive, flag as leak
                if slope > 50000.0:  # Growth > 50KB/tick
                    leak_detected = True

            forecasts[pod_name] = {
                "cpu_current": cpu_history[-1] if cpu_history else 0.0,
                "cpu_projected_1m": round(cpu_1m, 5),
                "cpu_projected_5m": round(cpu_5m, 5),
                "mem_current_bytes": mem_history[-1] if mem_history else 0.0,
                "mem_projected_1m_bytes": round(mem_1m, 1),
                "mem_projected_5m_bytes": round(mem_5m, 1),
                "memory_leak_detected": leak_detected
            }

        return forecasts

    def calculate_time_to_exhaustion(self, storage_state: dict) -> list[dict]:
        """
        Forecasts how long (in minutes) physical partitions or volume allocations
        can survive under current read/write rate dynamics.
        """
        tte_forecasts = []
        
        pvcs = storage_state.get("persistent_volume_claims", [])
        for pvc in pvcs:
            pvc_name = pvc["pvc_name"]
            capacity = pvc["capacity_gb"]
            used = pvc["used_gb"]
            free = max(0.0, capacity - used)

            # Store in rolling history list
            if pvc_name not in self._storage_history:
                self._storage_history[pvc_name] = []
            
            self._storage_history[pvc_name].append(used)
            if len(self._storage_history[pvc_name]) > 20:
                self._storage_history[pvc_name].pop(0)

            # Calculate actual growth/leak rate (GB per poll tick) using linear regression
            history = self._storage_history[pvc_name]
            leak_rate_gb_min = 0.0

            if len(history) >= 5:
                # Get regression slope
                slope = np.polyfit(np.arange(len(history)), np.array(history), 1)[0]
                # Convert GB/tick to GB/minute (1 tick = 5 seconds, so 12 ticks = 1 minute)
                if slope > 0.0:
                    leak_rate_gb_min = slope * 12.0

            # If no active regression slope is calculated, fallback to partition's active physical IO speed
            if leak_rate_gb_min == 0.0 and pvc.get("iops_write", 0) > 0:
                # physical write latency delta estimation (e.g. active write rate)
                # Let's approximate from live disk operations: assume average 4KB blocks
                leak_rate_gb_min = (pvc.get("iops_write", 0) * 4096.0 * 60.0) / 1e9

            if leak_rate_gb_min > 0.00001:
                minutes_remaining = free / leak_rate_gb_min
            else:
                minutes_remaining = float('inf')
            
            tte_forecasts.append({
                "volume": pvc["volume_name"],
                "target_pod": pvc["target_pod"],
                "percent_used": pvc["percent_used"],
                "leak_rate_gb_min": round(leak_rate_gb_min, 6),
                "minutes_remaining": round(minutes_remaining, 1) if minutes_remaining < 1e5 else "Infinite"
            })

        return tte_forecasts

    def predict_failures(self, forecasts: dict, anomalies: list[dict], network_anoms: list[dict], storage_anoms: list[dict]) -> list[dict]:
        """
        Computes a mathematical failure probability score (0.0 to 1.0)
        and predicts potential pod/process crashes or resource lockouts.
        """
        failure_predictions = []

        anomaly_pods = {a["pod"]: a for a in anomalies}
        # Gather active network flow names
        net_flow_names = [n["flow"] for n in network_anoms]

        for pod_name, f_data in forecasts.items():
            prob = 0.0
            indicators = []

            # Factor 1: CPU Spikes or saturation projections
            if f_data["cpu_projected_1m"] > 0.85:
                prob += 0.25
                indicators.append("Projected CPU Saturation (>85%)")
            elif f_data["cpu_projected_5m"] > 0.95:
                prob += 0.15
                indicators.append("Projected long-term CPU saturation")

            # Factor 2: Memory leak trajectories
            if f_data["memory_leak_detected"]:
                prob += 0.40
                indicators.append("Uncontrolled memory leak trend detected")

            # Factor 3: Active resource anomalies (Isolation Forest flags)
            if pod_name in anomaly_pods:
                prob += 0.20
                indicators.append(f"Isolation Forest flagged anomaly (Score: {anomaly_pods[pod_name]['anomaly_score']})")

            # Factor 4: Downstream network congestion links
            short_pod = pod_name.split("[")[0].strip()
            network_impact = False
            for net_flow in net_flow_names:
                if short_pod.lower() in net_flow.lower():
                    network_impact = True
                    break
            
            if network_impact:
                prob += 0.15
                indicators.append("Mounted socket connections suffering from RTT latency or interface packet drops")

            # Factor 5: Local physical storage limits reached
            if len(storage_anoms) > 0:
                prob += 0.20
                indicators.append("Host physical storage is bottlenecked, threatening IO operations")

            prob = min(0.99, prob)

            if prob > 0.30:
                failure_predictions.append({
                    "pod": pod_name,
                    "failure_probability": round(prob, 2),
                    "risk_level": "critical" if prob > 0.70 else "moderate",
                    "leading_indicators": indicators,
                    "recommended_action": "Trigger autoscaler or pre-emptively recycle process." if prob > 0.70 else "Monitor resource trends closely."
                })

        return failure_predictions

    def estimate_scaling_requirements(self, predictions: list[dict]) -> list[dict]:
        """
        Calculates reactive scaling actions (Horizontal Pod Autoscaling - HPA)
        needed to prevent predicted process/container exhaustion.
        """
        scaling_actions = []
        for pred in predictions:
            if pred["failure_probability"] > 0.50:
                pod_base = pred["pod"].split("[")[0].strip()
                risk = pred["risk_level"]
                
                if risk == "critical":
                    replicated_count = 3
                    rec = f"Scale up replicas of '{pod_base}' by +2 instantly to distribute request volumes."
                else:
                    replicated_count = 2
                    rec = f"Scale up replicas of '{pod_base}' by +1 to mitigate resource contention."
                
                scaling_actions.append({
                    "target_service": pod_base,
                    "current_risk": risk,
                    "probability_pct": int(pred["failure_probability"] * 100),
                    "recommended_replicas_delta": replicated_count - 1,
                    "action_details": rec
                })
        return scaling_actions
