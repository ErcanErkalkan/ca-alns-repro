
import json, matplotlib.pyplot as plt
from pathlib import Path

def plot_convergence(log_file, out_png):
    js = json.loads(Path(log_file).read_text())
    hist = js.get("convergence", [])
    x = [h[0] for h in hist]
    y = [h[1] for h in hist]
    plt.figure()
    plt.plot(x,y)
    plt.xlabel("Iteration block")
    plt.ylabel("Best fitness")
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=160, bbox_inches="tight")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--log", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    plot_convergence(a.log, a.out)
