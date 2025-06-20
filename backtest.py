import json
from allocator import allocate
from datetime import datetime
from itertools import product

# --- Helper functions ---
def compute_cost(split, venues, order_size, lambda_over, lambda_under, theta_queue):
    executed = 0
    cash_spent = 0
    for i in range(len(venues)):
        venue = venues[i]
        qty = split[i]
        exe = min(qty, venue['ask_size'])
        executed += exe
        cash_spent += exe * (venue['ask'] + venue['fee'])
        maker_rebate = max(qty - exe, 0) * venue['rebate']
        cash_spent -= maker_rebate
    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)
    risk_pen = theta_queue * (underfill + overfill)
    cost_pen = lambda_under * underfill + lambda_over * overfill
    return cash_spent + risk_pen + cost_pen

def best_ask_strategy(lines, order_size):
    total_cost = 0
    total_filled = 0
    remaining = order_size
    for line in lines:
        snapshot = json.loads(line)
        venues = snapshot["venues"]
        best = min(venues, key=lambda v: v['ask'])
        fill = min(best['ask_size'], remaining)
        total_cost += fill * (best['ask'] + best['fee'])
        remaining -= fill
        total_filled += fill
        if remaining <= 0:
            break
    avg_px = total_cost / total_filled if total_filled > 0 else 0
    return {"total_cash": total_cost, "avg_fill_px": avg_px}

def twap_strategy(lines, order_size, interval_seconds=60):
    total_cost = 0
    total_filled = 0
    chunk_size = order_size // 5
    last_time = None
    fill_buffer = []
    for line in lines:
        snapshot = json.loads(line)
        venues = snapshot["venues"]
        ts_str = snapshot["timestamp"]
        ts = datetime.strptime(ts_str, "%H:%M:%S")
        if last_time is None:
            last_time = ts
            fill_buffer = venues
            continue
        time_delta = (ts - last_time).total_seconds()
        if time_delta >= interval_seconds:
            best = min(fill_buffer, key=lambda v: v['ask'])
            fill = min(best['ask_size'], chunk_size)
            total_cost += fill * (best['ask'] + best['fee'])
            total_filled += fill
            last_time = ts
    avg_px = total_cost / total_filled if total_filled > 0 else 0
    return {"total_cash": total_cost, "avg_fill_px": avg_px}

def vwap_strategy(lines, order_size):
    total_cost = 0
    total_filled = 0
    remaining = order_size
    for line in lines:
        snapshot = json.loads(line)
        venues = snapshot["venues"]
        total_sz = sum(v["ask_size"] for v in venues)
        if total_sz == 0:
            continue
        for v in venues:
            portion = v["ask_size"] / total_sz
            fill = min(remaining, int(order_size * portion))
            cost = fill * (v["ask"] + v["fee"])
            total_cost += cost
            total_filled += fill
            remaining -= fill
            if remaining <= 0:
                break
        if remaining <= 0:
            break
    avg_px = total_cost / total_filled if total_filled > 0 else 0
    return {"total_cash": total_cost, "avg_fill_px": avg_px}

def bps(better, baseline):
    return round((baseline - better) / baseline * 10000, 2)

# --- Run everything ---
with open("mock_stream.json", "r") as f:
    lines = f.readlines()

order_size = 5000
lambda_options = [0.2, 0.4, 0.6]
theta_options = [0.1, 0.3, 0.5]
best_result = None

# --- Parameter tuning loop ---
for lam_over in lambda_options:
    for lam_under in lambda_options:
        for theta in theta_options:
            total_filled = 0
            total_cost = 0
            remaining = order_size
            for line in lines:
                snapshot = json.loads(line)
                venues = snapshot["venues"][:3]
                if remaining <= 0:
                    break
                step_size = min(500, remaining)
                split, cost = allocate(step_size, venues, lam_over, lam_under, theta)
                total_cost += cost
                total_filled += step_size
                remaining -= step_size
            avg_px = total_cost / total_filled if total_filled > 0 else float('inf')
            if best_result is None or avg_px < best_result['avg_fill_px']:
                best_result = {
                    "lambda_over": lam_over,
                    "lambda_under": lam_under,
                    "theta_queue": theta,
                    "total_cash": total_cost,
                    "avg_fill_px": avg_px
                }

# --- Baseline strategy comparison ---
baselines = {
    "best_ask": best_ask_strategy(lines, order_size),
    "twap": twap_strategy(lines, order_size),
    "vwap": vwap_strategy(lines, order_size)
}

# --- Final JSON output ---
output = {
    "best_parameters": {
        "lambda_over": best_result["lambda_over"],
        "lambda_under": best_result["lambda_under"],
        "theta_queue": best_result["theta_queue"]
    },
    "optimized": {
        "total_cash": best_result["total_cash"],
        "avg_fill_px": best_result["avg_fill_px"]
    },
    "baselines": baselines,
    "savings_vs_baselines_bps": {
        k: bps(best_result["avg_fill_px"], v["avg_fill_px"]) for k, v in baselines.items()
    }
}

print(json.dumps(output, indent=2))
