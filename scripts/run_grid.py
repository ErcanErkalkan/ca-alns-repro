#!/usr/bin/env python3
import argparse, os, subprocess, sys, shlex, importlib.util
from pathlib import Path

def _module_exists(modname: str) -> bool:
    # Güvenli kontrol: üst paket yoksa ModuleNotFoundError atmasın
    try:
        spec = importlib.util.find_spec(modname)
    except ModuleNotFoundError:
        return False
    return spec is not None

def _file_exists(path: str) -> bool:
    return Path(path).is_file()

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

    # Koşucu seçimi: önce modül, sonra dosya fallback
    runner_module = "experiments.run_experiment"
    run_as_module = False
    runner_file = None

    if _module_exists(runner_module):
        run_as_module = True
    else:
        # Modül yoksa olası dosya yollarını sırayla dene
        for cand in [
            "experiments/run_experiment.py",
            "run_experiment.py",
            "experiments/run_experiment_patched.py",
            "run_experiment_patched.py",
        ]:
            if _file_exists(cand):
                runner_file = cand
                break
        if runner_file is None:
            print("ERROR: 'experiments.run_experiment' modülü da yok, dosya da bulunamadı.\n"
                  "Lütfen aşağıdakilerden biri mevcut olsun:\n"
                  " - src/experiments/run_experiment.py (veya run_experiment_patched.py)\n"
                  " - proje kökünde run_experiment.py (veya run_experiment_patched.py)",
                  file=sys.stderr)
            sys.exit(1)

    for scale in args.scales:
        n_uav, n_tgt = scale_map[scale]
        for algo in args.algs:
            out_dir = os.path.join(args.runs_root, scale, algo)
            os.makedirs(out_dir, exist_ok=True)
            for seed in args.seeds:
                out_file = os.path.join(out_dir, f"seed_{seed}.json")
                if run_as_module:
                    cmd = [
                        sys.executable, "-m", runner_module,
                        "--algo", algo,
                        "--seed", str(seed),
                        "--E_max", str(args.e_max),
                        "--T_max", str(args.t_max),
                        "--out", out_file,
                        "--n_uav", str(n_uav),
                        "--n_targets", str(n_tgt),
                    ]
                else:
                    cmd = [
                        sys.executable, runner_file,
                        "--algo", algo,
                        "--seed", str(seed),
                        "--E_max", str(args.e_max),
                        "--T_max", str(args.t_max),
                        "--out", out_file,
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
