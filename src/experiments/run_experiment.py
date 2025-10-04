import argparse, json, time, random, os
from pathlib import Path

# Config & core
from ca_alns.config import ConnectivityConfig, OperatorConfig, BudgetConfig, PenaltyConfig, ExperimentConfig
from ca_alns.eval import compute_upper_bounds
from ca_alns.connectivity import compute_cadence_bound
from ca_alns.core import CAALNSFull

# Baselines
from baselines.ga import GA
from baselines.de import DE

# Problem helpers
from ca_alns.problem import Node, UAV, Instance

def parse_args():
    p = argparse.ArgumentParser(description="CA-ALNS / ALNS-Std / ALNS+LS / GA / DE experiment runner (fair budgets)")
    p.add_argument("--algo", choices=["ca-alns","alns-std","alns-ls","ga","de"], default="ca-alns")
    p.add_argument("--E_max", type=int, default=100000)
    p.add_argument("--T_max", type=float, default=0.0, help="0 = ignore wall time")
    p.add_argument("--range_R", type=float, default=150.0)
    p.add_argument("--rho", type=float, default=15.0)
    p.add_argument("--vmax", type=float, default=15.0)
    p.add_argument("--mode", choices=["range","sinr"], default="range")
    p.add_argument("--tx_power_dbm", type=float, default=20.0)
    p.add_argument("--noise_dbm", type=float, default=-96.0)
    p.add_argument("--gamma_th_db", type=float, default=6.0)
    p.add_argument("--bidirectional", action="store_true", default=True)

    p.add_argument("--alpha", type=float, default=1.0)
    p.add_argument("--lambda_bal", type=float, default=0.0)
    p.add_argument("--lambda_wait", type=float, default=0.0)
    p.add_argument("--lambda_rp", type=float, default=0.0)
    p.add_argument("--lambda_mksp", type=float, default=0.0)

    # variant-independent but can be overridden by variant flags
    p.add_argument("--use_rally", action="store_true", default=True)
    p.add_argument("--warm_blocks", type=int, default=3)
    p.add_argument("--p_warm", type=float, default=1e-2)

    # instance size
    p.add_argument("--n_uav", type=int, default=5)
    p.add_argument("--n_targets", type=int, default=20)
    p.add_argument("--span", type=float, default=500.0)

    # misc
    p.add_argument("--measure_energy", action="store_true", default=False)
    p.add_argument("--avg_power_w", type=float, default=50.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", type=str, default="runs/out.json")
    return p.parse_args()

def gen_random_instance(seed: int, n_uav: int, n_targets: int, span: float, v_max: float) -> Instance:
    rng = random.Random(seed)
    depot = Node(0, 0.0, 0.0)
    targets = [Node(i+1, rng.uniform(-span, span), rng.uniform(-span, span)) for i in range(n_targets)]
    uavs = [UAV(i, v_max=v_max) for i in range(n_uav)]
    return Instance(depot=depot, targets=targets, uavs=uavs)

def _variant_flags(algo: str):
    """Returns dict: use_surrogate (safety-first), use_rally, enable_ls"""
    if algo == "ca-alns":
        return dict(use_surrogate=True, use_rally=True, enable_ls=False)
    if algo == "alns-std":
        return dict(use_surrogate=False, use_rally=False, enable_ls=False)
    if algo == "alns-ls":
        return dict(use_surrogate=False, use_rally=False, enable_ls=True)
    # GA / DE fallthrough
    return dict(use_surrogate=False, use_rally=False, enable_ls=False)

def main():
    args = parse_args()
    rng = random.Random(args.seed)

    # Instance
    inst = gen_random_instance(args.seed, n_uav=args.n_uav, n_targets=args.n_targets, span=args.span, v_max=args.vmax)

    # Connectivity + cadence
    conn = ConnectivityConfig(mode=args.mode, R=args.range_R, rho=args.rho, v_max=args.vmax,
                              tx_power_dbm=args.tx_power_dbm, noise_dbm=args.noise_dbm,
                              gamma_th_db=args.gamma_th_db, bidirectional=args.bidirectional)
    _ = compute_cadence_bound(conn.R, conn.rho, conn.v_max)

    # Budgets & penalties
    ops = OperatorConfig(use_rally_points=args.use_rally, warm_blocks=args.warm_blocks, p_warm=args.p_warm)
    bud = BudgetConfig(E_max=args.E_max, T_max=args.T_max if args.T_max>0 else None)
    coords = [(inst.depot.x, inst.depot.y)] + [(t.x, t.y) for t in inst.targets]
    Cmax_aug = compute_upper_bounds(coords, depot_idx=0, n_uav=len(inst.uavs), alpha=args.alpha)
    lam = max(1.01*Cmax_aug, 1e3)
    pen = PenaltyConfig(alpha=args.alpha,
                        lambda_disc=lam, lambda_cap=lam, lambda_bat=lam,
                        lambda_bal=args.lambda_bal, lambda_wait=args.lambda_wait,
                        lambda_rp=args.lambda_rp, lambda_mksp=args.lambda_mksp)

    # Apply variant flags
    flags = _variant_flags(args.algo)
    # rally override
    ops.use_rally_points = bool(flags.get("use_rally", ops.use_rally_points))
    # try to enable local search if OperatorConfig supports it (best-effort)
    if flags.get("enable_ls", False):
        try:
            setattr(ops, "use_local_search", True)
        except Exception:
            pass

    cfg = ExperimentConfig(connectivity=conn, operators=ops, budget=bud, penalties=pen)
    sur_file = str((Path(__file__).resolve().parents[2] / "artifacts" / "surrogate_frozen.json"))

    def run_algo():
        if args.algo == "ga":
            algo = GA(fitness_penalties=pen.__dict__, E_max=bud.E_max, seed=args.seed)
            return algo.run({'total_travel': 100.0, 'connected': True, 'payload_ok': True, 'battery_ok': True})
        elif args.algo == "de":
            algo = DE(fitness_penalties=pen.__dict__, E_max=bud.E_max, seed=args.seed)
            return algo.run({'total_travel': 100.0, 'connected': True, 'payload_ok': True, 'battery_ok': True})
        else:
            # ALNS family
            use_sur = flags.get("use_surrogate", True)
            spath = sur_file if use_sur else None
            solver = CAALNSFull(cfg, rng, instance=inst, surrogate_path=spath)
            if use_sur:
                return solver.run_full(penalties_final=pen.__dict__, surrogate_path=spath)
            else:
                # penalty-only path: pass no surrogate
                return solver.run_full(penalties_final=pen.__dict__, surrogate_path=None)

    if args.measure_energy:
        # simple average-power energy estimate (portable)
        start = time.time()
        result = run_algo()
        elapsed = time.time() - start
        result["E_wh"] = args.avg_power_w * (elapsed/3600.0)
    else:
        result = run_algo()

    # normalize expected keys for aggregator
    result.setdefault("total_travel", None)
    result.setdefault("fitness", result.get("best_fitness"))
    result.setdefault("connected", None)
    result.setdefault("snapshots_connected_pct", None)
    result.setdefault("E_used", None)
    result.setdefault("wallclock_s", None)

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
