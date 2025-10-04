#!/usr/bin/env python3
import argparse, glob, json, os, pandas as pd

def parse_one(fp):
    with open(fp, "r") as f:
        try:
            d = json.load(f)
        except Exception:
            return None
    parts = fp.split(os.sep)
    try:
        algo = parts[-2]
        dataset = parts[-3]
    except:
        algo, dataset = "unknown","unknown"
    seed = -1
    base = os.path.splitext(os.path.basename(fp))[0]
    if base.startswith("seed_"):
        try:
            seed = int(base.split("_")[1])
        except:
            pass
    out = {
        "path": fp,
        "dataset": dataset,
        "algo": algo,
        "seed": seed,
        "total_travel": d.get("total_travel"),
        "best_fitness": d.get("fitness"),
        "connected_final": d.get("connected"),
        "snapshots_connected_pct": d.get("snapshots_connected_pct"),
        "evals_used": d.get("E_used"),
        "wallclock_s": d.get("wallclock_s"),
    }
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", required=True)
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()

    rows = []
    for fp in glob.glob(args.glob, recursive=True):
        rec = parse_one(fp)
        if rec: rows.append(rec)

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    print("Wrote", args.out_csv, "rows:", len(df))

if __name__ == "__main__":
    main()
