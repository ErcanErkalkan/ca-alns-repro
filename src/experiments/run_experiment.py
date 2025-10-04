
import argparse, json, time, random
from pathlib import Path
from ca_alns.config import ConnectivityConfig, OperatorConfig, BudgetConfig, PenaltyConfig, ExperimentConfig
from ca_alns.eval import compute_upper_bounds, fitness_value
from ca_alns.core import CAALNS
from ca_alns.energy import measure_energy_wh
from ca_alns.connectivity import compute_cadence_bound
from baselines.ga import GA
from baselines.de import DE

def parse_args():
    p = argparse.ArgumentParser(description="CA-ALNS / GA / DE experiment runner with fairness")
    p.add_argument("--algo", choices=["ca-alns","ga","de"], default="ca-alns")
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

    p.add_argument("--use_rally", action="store_true", default=True)
    p.add_argument("--warm_blocks", type=int, default=3)
    p.add_argument("--p_warm", type=float, default=1e-2)

    p.add_argument("--measure_energy", action="store_true", default=False)
    p.add_argument("--avg_power_w", type=float, default=50.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", type=str, default="runs/out.json")
    return p.parse_args()

def main():
    args = parse_args()
    rng = random.Random(args.seed)

    conn = ConnectivityConfig(mode=args.mode, R=args.range_R, rho=args.rho, v_max=args.vmax,
                              tx_power_dbm=args.tx_power_dbm, noise_dbm=args.noise_dbm,
                              gamma_th_db=args.gamma_th_db, bidirectional=args.bidirectional)
    # auto cadence if None
    delta_tau = compute_cadence_bound(conn.R, conn.rho, conn.v_max)

    ops = OperatorConfig(use_rally_points=args.use_rally, warm_blocks=args.warm_blocks, p_warm=args.p_warm)
    bud = BudgetConfig(E_max=args.E_max, T_max=args.T_max if args.T_max>0 else None)

    # Penalty calibration: set disc/cap/bat high using upper bound proxy
    coords = [(0.0,0.0)] + [(10.0,0.0), (0.0,10.0)]  # placeholder geometry
    Cmax_aug = compute_upper_bounds(coords, depot_idx=0, n_uav=2, alpha=args.alpha)
    lam = max(1.01*Cmax_aug, 1e3)
    pen = PenaltyConfig(alpha=args.alpha,
                        lambda_disc=lam, lambda_cap=lam, lambda_bat=lam,
                        lambda_bal=args.lambda_bal, lambda_wait=args.lambda_wait,
                        lambda_rp=args.lambda_rp, lambda_mksp=args.lambda_mksp)

    cfg = ExperimentConfig(connectivity=conn, operators=ops, budget=bud, penalties=pen)

    # seed initial solution
    init = {'total_travel': 100.0, 'connected': True, 'payload_ok': True, 'battery_ok': True,
            'workload_max': 60.0, 'workload_min': 40.0, 'rally_points_count': 0, 'rally_wait_sum': 0.0,
            'mean_insert_cost': 10.0}

    def run_algo():
        if args.algo == "ga":
            algo = GA(fitness_penalties=pen.__dict__, E_max=bud.E_max, seed=args.seed)
            return algo.run(init)
        elif args.algo == "de":
            algo = DE(fitness_penalties=pen.__dict__, E_max=bud.E_max, seed=args.seed)
            return algo.run(init)
        else:
            solver = CAALNS(cfg, rng)
            return solver.run(init, penalties_final=pen.__dict__)

    if args.measure_energy:
        result, E_wh = measure_energy_wh(run_algo, avg_power_w=args.avg_power_w)
        result['E_wh'] = E_wh
    else:
        result = run_algo()

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

# old main removed


from ca_alns.problem import Node, UAV, Instance
from ca_alns.core import CAALNSFull
from ca_alns.surrogate import FrozenSurrogate

def gen_random_instance(seed: int, n_uav: int = 5, n_targets: int = 20, span: float = 500.0, v_max: float = 15.0) -> Instance:
    rng = random.Random(seed)
    depot = Node(0, 0.0, 0.0)
    targets = [Node(i+1, rng.uniform(-span, span), rng.uniform(-span, span)) for i in range(n_targets)]
    uavs = [UAV(i, v_max=v_max) for i in range(n_uav)]
    return Instance(depot=depot, targets=targets, uavs=uavs)

def main():
    args = parse_args()
    rng = random.Random(args.seed)

    inst = gen_random_instance(args.seed, n_uav=5, n_targets=20, span=500.0, v_max=args.vmax)

    conn = ConnectivityConfig(mode=args.mode, R=args.range_R, rho=args.rho, v_max=args.vmax,
                              tx_power_dbm=args.tx_power_dbm, noise_dbm=args.noise_dbm,
                              gamma_th_db=args.gamma_th_db, bidirectional=args.bidirectional)
    delta_tau = compute_cadence_bound(conn.R, conn.rho, conn.v_max)

    ops = OperatorConfig(use_rally_points=args.use_rally, warm_blocks=args.warm_blocks, p_warm=args.p_warm)
    bud = BudgetConfig(E_max=args.E_max, T_max=args.T_max if args.T_max>0 else None)

    coords = [(inst.depot.x, inst.depot.y)] + [(t.x, t.y) for t in inst.targets]
    Cmax_aug = compute_upper_bounds(coords, depot_idx=0, n_uav=len(inst.uavs), alpha=args.alpha)
    lam = max(1.01*Cmax_aug, 1e3)
    pen = PenaltyConfig(alpha=args.alpha,
                        lambda_disc=lam, lambda_cap=lam, lambda_bat=lam,
                        lambda_bal=args.lambda_bal, lambda_wait=args.lambda_wait,
                        lambda_rp=args.lambda_rp, lambda_mksp=args.lambda_mksp)

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
            solver = CAALNSFull(cfg, rng, instance=inst, surrogate_path=sur_file)
            return solver.run_full(penalties_final=pen.__dict__, surrogate_path=sur_file)

    if args.measure_energy:
        result, E_wh = measure_energy_wh(run_algo, avg_power_w=args.avg_power_w)
        result['E_wh'] = E_wh
    else:
        result = run_algo()

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
