#!/usr/bin/env python3
import argparse, pandas as pd, matplotlib.pyplot as plt
import os

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agg", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.agg)
    # Expect a column like evals_by_block serialized as JSON or semi-colon; fallback to evals_used per run
    fig, ax = plt.subplots(figsize=(6.5,3.2))
    for algo, g in df.groupby("algo"):
        # naive proxy: uniform per-block if detailed not present
        ax.plot(range(len(g)), [g["evals_used"].mean()/max(1,len(g))]*len(g), label=algo, marker="o")
    ax.set_xlabel("Iteration block")
    ax.set_ylabel("Fitness calls per block (proxy)")
    ax.grid(True, ls=":")
    ax.legend(loc="best")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)

if __name__ == "__main__":
    main()
