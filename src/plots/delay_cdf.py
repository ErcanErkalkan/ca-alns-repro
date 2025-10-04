
import numpy as np, matplotlib.pyplot as plt
from pathlib import Path

def plot_delay_cdf(csv_path, out_png):
    import pandas as pd
    x = pd.read_csv(csv_path)["delay_ms"].values
    xs = np.sort(x)
    ys = np.linspace(0,1,len(xs))
    plt.figure()
    plt.plot(xs, ys)
    plt.xlabel("End-to-end delay (ms)")
    plt.ylabel("CDF")
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=160, bbox_inches="tight")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    plot_delay_cdf(a.csv, a.out)
