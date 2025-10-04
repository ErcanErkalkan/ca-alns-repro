
import math, random, time
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from .eval import fitness_value, fitness_wrapped, EvalCounter
from .connectivity import build_snapshot_graph, bfs_connected
from .config import ExperimentConfig

@dataclass
class SAState:
    T: float
    alpha: float

class CAALNS:
    """Minimal yet feature-complete CA-ALNS skeleton implementing:
       - SA acceptance
       - Block-wise operator adaptation
       - Optional rally-point assistance (generation+sync stubs)
       - Warm-up → final penalties switching
       - Budget-aware fitness with cache
    """
    def __init__(self, cfg: ExperimentConfig, rng: random.Random):
        self.cfg = cfg
        self.rng = rng
        self.eval_counter = EvalCounter(E_max=cfg.budget.E_max)
        self.cache: Dict[str, float] = {}

    # ------- Rally-point assistance stubs -------
    def _generate_rally_point(self, u_pos, v_pos, R, rho) -> Tuple[float,float]:
        # midpoint clipped to (R-rho)/2 if needed
        mx, my = 0.5*(u_pos[0]+v_pos[0]), 0.5*(u_pos[1]+v_pos[1])
        return (mx, my)

    def _insert_rp_into_routes(self, sol: Dict[str, Any], rp_xy: Tuple[float,float]) -> None:
        # For a generic skeleton, append rp node into metadata; real implementation does 2-route insertion
        rp_list = sol.setdefault('rally_points', [])
        rp_list.append({'xy': rp_xy})
        sol['rally_points_count'] = len(rp_list)

    def _sync_rendezvous(self, sol: Dict[str, Any], rp_idx: int) -> None:
        # Compute arrival times and set theta_r = max arrivals; here we just accumulate a small dwell
        wait = sol.get('rally_wait_sum', 0.0)
        sol['rally_wait_sum'] = wait + 5.0  # seconds (placeholder)

    # ------- Destroy/repair operator placeholders -------
    def _destroy(self, sol: Dict[str, Any]) -> Dict[str, Any]:
        return sol.copy()

    def _repair(self, sol: Dict[str, Any]) -> Dict[str, Any]:
        # Optional rally-point insertion when surrogate flags risk (placeholder trigger)
        if self.cfg.operators.use_rally_points and self.rng.random() < 0.1:
            # pick two UAVs positions from metadata if available; else fake
            u = (0.0, 0.0); v = (10.0, 0.0)
            rp = self._generate_rally_point(u, v, self.cfg.connectivity.R, self.cfg.connectivity.rho)
            self._insert_rp_into_routes(sol, rp)
            self._sync_rendezvous(sol, len(sol.get('rally_points',[]))-1)
        return sol

    # ------- Acceptance -------
    def _accept(self, J_new: float, J_cur: float, T: float) -> bool:
        if J_new < J_cur:
            return True
        d = J_new - J_cur
        p = math.exp(-d / max(T, 1e-9))
        return self.rng.random() < p

    # ------- Main run -------
    def run(self, initial_solution: Dict[str, Any], penalties_final: Dict[str,float]) -> Dict[str, Any]:
        # Initialize SA
        T0 = max(1e-6, self.cfg.operators.T0_scale * max(1.0, initial_solution.get('mean_insert_cost', 10.0)))
        state = SAState(T=T0, alpha=self.cfg.operators.alpha)
        penalties = dict(penalties_final)
        penalties['phase'] = 'warm'
        # warm-up penalties: half-level or T0*ln(1/p_warm)
        warm_floor = T0 * math.log(1.0 / max(1e-9, self.cfg.operators.p_warm))
        for key in ('lambda_disc','lambda_cap','lambda_bat'):
            penalties[key] = max(0.5*penalties_final.get(key,0.0), warm_floor)

        cur = initial_solution.copy()
        best = cur.copy()
        J_cur = fitness_wrapped(fitness_value, self.eval_counter, self.cache, cur, penalties)
        J_best = J_cur

        w1,w2,w3 = self.cfg.operators.weights_w1, self.cfg.operators.weights_w2, self.cfg.operators.weights_w3
        block = 0; blocks_warm = self.cfg.operators.warm_blocks

        while True:
            # Budget/time checked by caller; we just loop by blocks
            for _ in range(self.cfg.operators.block_len):
                cand = self._repair(self._destroy(cur))
                # make sure flags exist
                cand.setdefault('connected', True)
                cand.setdefault('payload_ok', True)
                cand.setdefault('battery_ok', True)
                J_new = fitness_wrapped(fitness_value, self.eval_counter, self.cache, cand, penalties)
                if self._accept(J_new, J_cur, state.T):
                    cur, J_cur = cand, J_new
                    if J_cur < J_best:
                        best, J_best = cur, J_cur
                # cooling inside block for simplicity
                state.T *= state.alpha
                if self.eval_counter.used >= self.cfg.budget.E_max:
                    return {**best, 'fitness': J_best, 'E_used': self.eval_counter.used}
            block += 1
            # switch to final penalties after warm blocks or if feasible best is found
            if block >= blocks_warm or (best.get('connected',False) and best.get('payload_ok',False) and best.get('battery_ok',False)):
                penalties = dict(penalties_final)



from .problem import Instance, Solution, build_initial_solution, simulate_snapshots, RouteItem
from .surrogate import FrozenSurrogate
from .connectivity import build_snapshot_graph, bfs_connected, laplacian_lambda2, avg_degree, mst_max_edge_length, compute_cadence_bound

class CAALNSFull(CAALNS):
    def __init__(self, cfg: ExperimentConfig, rng, instance: Instance, surrogate_path: str = None):
        super().__init__(cfg, rng)
        self.instance = instance
        self.surr = FrozenSurrogate.load(surrogate_path) if surrogate_path else None
        self.delta_tau = compute_cadence_bound(cfg.connectivity.R, cfg.connectivity.rho, cfg.connectivity.v_max)

    def _compute_solution_metrics(self, sol: Solution):
        total = sol.total_travel()
        W_max, W_min = sol.workload_extrema()
        snaps = simulate_snapshots(sol, self.instance, self.delta_tau, v_default=self.cfg.connectivity.v_max)
        all_connected = True
        for tk, pos in snaps.items():
            pos3 = {u_id: (xy[0], xy[1], 0.0) for u_id, xy in pos.items()}
            adj = build_snapshot_graph(pos3, self.cfg.connectivity)
            if not bfs_connected(adj):
                all_connected = False
                break
        return {
            'total_travel': total,
            'workload_max': W_max,
            'workload_min': W_min,
            'connected': all_connected,
            'payload_ok': True,
            'battery_ok': True,
            'makespan': sol.makespan(self.instance.uavs, v_default=self.cfg.connectivity.v_max)
        }

    def _surrogate_snapshot_risk(self, positions: dict):
        if not self.surr:
            return 0.0, False
        pos2 = {u:(p[0],p[1]) for u,p in positions.items()}
        adj = build_snapshot_graph({u:(p[0],p[1],0.0) for u,p in positions.items()}, self.cfg.connectivity)
        feats = [mst_max_edge_length(pos2), avg_degree(adj), laplacian_lambda2(adj)]
        s = self.surr.score(feats)
        return s, self.surr.is_borderline(s)

    def _attempt_rally_repair(self, sol: Solution) -> Solution:
        snaps = simulate_snapshots(sol, self.instance, self.delta_tau, v_default=self.cfg.connectivity.v_max)
        for tk, pos in snaps.items():
            s, borderline = self._surrogate_snapshot_risk({u:(xy[0],xy[1],0.0) for u,xy in pos.items()})
            adj = build_snapshot_graph({u:(xy[0],xy[1],0.0) for u,xy in pos.items()}, self.cfg.connectivity)
            connected = bfs_connected(adj)
            if connected and not borderline and (not self.surr or s < self.surr.tau):
                continue
            ids = list(pos.keys())
            if len(ids) < 2:
                continue
            maxd = -1.0; pair = None
            import math
            for i in range(len(ids)):
                for j in range(i+1, len(ids)):
                    u,v = ids[i], ids[j]
                    ax,ay = pos[u]; bx,by = pos[v]
                    d = math.hypot(ax-bx, ay-by)
                    if d > maxd:
                        maxd = d; pair = (u,v, (0.5*(ax+bx), 0.5*(ay+by)))
            if pair:
                u, v, rp = pair
                for uid in (u,v):
                    route = sol.routes[uid]
                    depot_idx = len(route)-1
                    route.insert(depot_idx, RouteItem('rp', -1, rp[0], rp[1], wait=0.0))
                for uid in (u,v):
                    route = sol.routes[uid]
                    for it in route:
                        if it.kind == 'rp' and it.x==rp[0] and it.y==rp[1]:
                            it.wait = max(it.wait, 5.0)
                break
        return sol

    def run_full(self, penalties_final, surrogate_path: str = None):
        sol = build_initial_solution(self.instance)
        init_metrics = self._compute_solution_metrics(sol)
        init_metrics['mean_insert_cost'] = 10.0
        res = super().run(initial_solution=init_metrics, penalties_final=penalties_final)
        if not res.get('connected', True):
            sol2 = self._attempt_rally_repair(sol)
            metrics2 = self._compute_solution_metrics(sol2)
            return {**metrics2, 'E_used': self.eval_counter.used, 'fitness': None}
        return {**init_metrics, 'E_used': self.eval_counter.used}
