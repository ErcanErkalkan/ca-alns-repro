#!/usr/bin/env python3
import argparse, pandas as pd, matplotlib.pyplot as plt
import os

def size_from_dataset(x):
    if x.lower().startswith("small"): return 20
    if x.lower().startswith("medium"): return 50
    if x.lower().startswith("large"): return 100
    if x.lower().startswith("xl"): return 1000
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agg", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.agg)
    df["m"] = df["dataset"].apply(size_from_dataset)
    fig, ax = plt.subplots(figsize=(6.8,3.4))
    for algo, g in df.groupby("algo"):
        gg = g.groupby("m")["wallclock_s"].median().reset_index()
        ax.plot(gg["m"], gg["wallclock_s"], marker="o", label=algo)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of targets m")
    ax.set_ylabel("Wall-clock time (s, median)")
    ax.grid(True, ls=":")
    ax.legend(loc="best")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)

if __name__ == "__main__":
    main()
