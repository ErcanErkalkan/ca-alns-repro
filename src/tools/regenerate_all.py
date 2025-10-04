
import subprocess, sys
from pathlib import Path

def run_cmd(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    Path("runs").mkdir(exist_ok=True, parents=True)
    for algo in ["ca-alns", "alns-ls"]:
        out = f"runs/{algo}_seed0.json"
        run_cmd([sys.executable, "-m", "experiments.run_experiment",
                 "--algo", algo, "--seed", "0", "--out", out])
    run_cmd([sys.executable, "-m", "analysis.aggregate_results",
             "--glob", "runs/*.json", "--out_csv", "analysis/summary.csv"])
    print("Done.")

if __name__ == "__main__":
    main()
