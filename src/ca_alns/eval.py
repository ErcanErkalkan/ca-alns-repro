
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import math
import hashlib
import json

@dataclass
class EvalCounter:
    E_max: int
    used: int = 0

    def tick(self, n: int = 1):
        self.used += n
        if self.used > self.E_max:
            raise RuntimeError(f"Evaluation budget exceeded: used={self.used} > E_max={self.E_max}")

def hash_solution(sol: Dict[str, Any]) -> str:
    # A generic, order-independent hash for caching
    def freeze(x):
        if isinstance(x, dict):
            return {k: freeze(x[k]) for k in sorted(x)}
        elif isinstance(x, list):
            return [freeze(v) for v in x]
        else:
            return x
    payload = json.dumps(freeze(sol), sort_keys=True, separators=(',',':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def compute_upper_bounds(coords, depot_idx: int, n_uav: int, alpha: float) -> float:
    """Compute C_max^{aug} rough upper bound using MST-like star proxy.
    coords: list of (x,y) for depot+targets
    depot_idx: index of depot in coords
    n_uav: number of UAVs
    alpha: travel cost weight
    Returns C_max^{aug}.
    """
    # depot-star sum
    import math
    def dist(a,b):
        return math.hypot(a[0]-b[0], a[1]-b[1])
    v0 = coords[depot_idx]
    W_star = sum(dist(v0, coords[j]) for j in range(len(coords)) if j != depot_idx)
    R_max = max((dist(v0, coords[j]) for j in range(len(coords)) if j != depot_idx), default=0.0)
    # crude MST upper bound proxy:  use star as proxy if MST not available
    C_travel = alpha * min(n_uav * 2.0 * W_star, (2.0*W_star + 2.0*n_uav*R_max))
    # workload imbalance bound requires B_max; caller can add if desired
    return C_travel

def fitness_value(solution: Dict[str, Any], penalties: Dict[str, float]) -> float:
    """Assemble fitness with penalties (Eq. (fitness) in paper).
    Expected keys (if present): 
      total_travel, connected(bool), payload_ok(bool), battery_ok(bool),
      workload_max, workload_min, rally_points_count, rally_wait_sum
    Missing keys default to safe values.
    """
    alpha = penalties.get('alpha', 1.0)
    lam_disc = penalties.get('lambda_disc', 0.0)
    lam_cap  = penalties.get('lambda_cap',  0.0)
    lam_bat  = penalties.get('lambda_bat',  0.0)
    lam_bal  = penalties.get('lambda_bal',  0.0)
    lam_wait = penalties.get('lambda_wait', 0.0)
    lam_rp   = penalties.get('lambda_rp',   0.0)
    lam_mksp = penalties.get('lambda_mksp', 0.0)
    H_max    = penalties.get('H_max', None)

    total_travel = float(solution.get('total_travel', 0.0))
    connected = bool(solution.get('connected', True))
    payload_ok = bool(solution.get('payload_ok', True))
    battery_ok = bool(solution.get('battery_ok', True))
    W_max = float(solution.get('workload_max', total_travel))
    W_min = float(solution.get('workload_min', 0.0))
    rp_count = int(solution.get('rally_points_count', 0))
    wait_sum = float(solution.get('rally_wait_sum', 0.0))
    mksp = float(solution.get('makespan', 0.0))

    J = alpha * total_travel
    if not connected:
        J += lam_disc
    if not payload_ok:
        J += lam_cap
    if not battery_ok:
        J += lam_bat
    J += lam_bal * max(0.0, W_max - W_min)
    J += lam_wait * max(0.0, wait_sum)
    J += lam_rp * max(0, rp_count)
    if H_max is not None and mksp > H_max:
        J += lam_mksp
    return J

def fitness_wrapped(fitness_fn, eval_counter: EvalCounter, cache: Dict[str, float], solution: Dict[str, Any], penalties: Dict[str,float]) -> float:
    """Cache-aware budget-compliant fitness wrapper.
    """
    h = hash_solution(solution)
    if h in cache:
        return cache[h]
    eval_counter.tick(1)
    J = fitness_fn(solution, penalties)
    cache[h] = J
    return J

# IPkWh metrics (Eq. ipkwh)
def improvement_per_kwh(J_ref: float, J_alg: float, E_wh: float) -> float:
    if E_wh <= 0: 
        return float('inf') if J_alg < J_ref else 0.0
    return (100.0 * (J_ref - J_alg) / max(J_ref, 1e-9)) / (E_wh / 1000.0)

def improvement_abs_per_kwh(J_ref: float, J_alg: float, E_wh: float) -> float:
    if E_wh <= 0: 
        return float('inf') if J_alg < J_ref else 0.0
    return (J_ref - J_alg) / (E_wh / 1000.0)
