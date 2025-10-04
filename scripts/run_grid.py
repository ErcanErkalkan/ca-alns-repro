#!/usr/bin/env python3
import argparse, os, subprocess, sys, shlex

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs_root", required=True)
    p.add_argument("--e_max", type=int, default=100000)
    p.add_argument("--t_max", type=int, default=600)
    p.add_argument("--scales", nargs="+", default=["Small","Medium","Large"])
    p.add_argument("--algs", nargs="+", default=["de","ga","alns-std","alns-ls","ca-alns"])
    p.add_argument("--seeds", nargs="+", default=[str(i) for i in range(30)])
    p.add_argument("--small", nargs=2, type=int, default=[5,20])
    p.add_argument("--medium", nargs=2, type=int, default=[10,50])
    p.add_argument("--large", nargs=2, type=int, default=[20,100])
    p.add_argument("--xl", nargs=2, type=int, default=[50,1000])
    args = p.parse_args()

    scale_map = {
        "Small": args.small,
        "Medium": args.medium,
        "Large": args.large,
        "XL": args.xl,
    }

    for scale in args.scales:
        n_uav, n_tgt = scale_map[scale]
        for algo in args.algs:
            out_dir = os.path.join(args.runs_root, scale, algo)
            os.makedirs(out_dir, exist_ok=True)
            for seed in args.seeds:
                out_file = os.path.join(out_dir, f"seed_{seed}.json")
                cmd = [
                    sys.executable, "-m", "experiments.run_experiment",
                    "--algo", algo,
                    "--seed", str(seed),
                    "--E_max", str(args.e_max),
                    "--T_max", str(args.t_max),
                    "--out", out_file,
                    # The following two require a tiny patch to run_experiment.py:
                    "--n_uav", str(n_uav),
                    "--n_targets", str(n_tgt),
                ]
                print("RUN:", " ".join(shlex.quote(c) for c in cmd))
                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    print("FAILED:", e)
                    continue

if __name__ == "__main__":
    main()
