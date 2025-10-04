
import numpy as np, matplotlib.pyplot as plt
from pathlib import Path

def plot_pdr_heatmap(csv_path, out_png):
    import pandas as pd
    df = pd.read_csv(csv_path, index_col=0)
    M = df.values
    plt.figure()
    plt.imshow(M, aspect='auto')
    plt.colorbar(label="PDR (%)")
    plt.xlabel("Receiver UAV idx")
    plt.ylabel("Sender UAV idx")
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=160, bbox_inches="tight")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    plot_pdr_heatmap(a.csv, a.out)
