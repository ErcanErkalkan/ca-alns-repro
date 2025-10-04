#!/usr/bin/env python3
import argparse, pandas as pd, numpy as np, json, os
from scipy.stats import wilcoxon

def median_iqr(x):
    x = np.asarray(x, dtype=float)
    if len(x)==0: return ("NA","NA")
    med = np.median(x)
    q1 = np.percentile(x, 25)
    q3 = np.percentile(x, 75)
    return (med, (q3-q1))

def bootstrap_ci(x, reps=10000, alpha=0.05, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    if len(x)==0: return (np.nan, np.nan)
    boots = []
    n = len(x)
    for _ in range(reps):
        s = rng.choice(x, size=n, replace=True)
        boots.append(np.median(s))
    lo = np.percentile(boots, 100*alpha/2)
    hi = np.percentile(boots, 100*(1-alpha/2))
    return (lo, hi)

def cliffs_delta(a, b):
    # proportion of pairwise wins minus losses (lower-is-better metrics sign flip handled upstream)
    a = np.asarray(a); b = np.asarray(b)
    wins = 0; losses = 0
    for ai in a:
        wins += np.sum(ai > b)
        losses += np.sum(ai < b)
    n = len(a)*len(b)
    if n==0: return np.nan
    return (wins - losses) / n

def a12(a, b):
    a = np.asarray(a); b=np.asarray(b)
    wins = 0
    for ai in a:
        wins += np.sum(ai > b)
    n = len(a)*len(b)
    if n==0: return np.nan
    return wins / n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs_csv", required=True)
    ap.add_argument("--out_tex", required=True)
    ap.add_argument("--out_json", default=None)
    ap.add_argument("--caption", default="Performance")
    ap.add_argument("--label", default="tab:perf")
    args = ap.parse_args()

    df = pd.read_csv(args.runs_csv)

    # Expected columns (some optional): dataset, algo, seed, total_travel, best_fitness, connected_final, snapshots_connected_pct, evals_used, wallclock_s
    datasets = sorted(df["dataset"].unique())
    algos = sorted(df["algo"].unique())

    # TABLE 1: Performance (median [IQR], 95% CI for median) + Connectivity rates
    rows = []
    stats_map = {}
    for ds in datasets:
        dsub = df[df.dataset==ds]
        for algo in algos:
            g = dsub[dsub.algo==algo]
            if g.empty: continue
            med_cost, iqr_cost = median_iqr(g["total_travel"].dropna())
            ci_lo, ci_hi = bootstrap_ci(g["total_travel"].dropna())
            med_time, iqr_time = median_iqr(g["wallclock_s"].dropna())
            conn_rate = 100.0 * g["connected_final"].fillna(False).astype(int).mean()
            snap_conn = g.get("snapshots_connected_pct", pd.Series(dtype=float))
            snap_conn = 100.0 * np.nanmean(snap_conn) if len(snap_conn)>0 else np.nan
            rows.append([ds, algo, med_cost, iqr_cost, ci_lo, ci_hi, med_time, iqr_time, conn_rate, snap_conn])
            stats_map.setdefault(ds, {})[algo] = {"median_cost": med_cost, "iqr_cost": iqr_cost,
                                                  "ci": [ci_lo, ci_hi], "median_time": med_time, "iqr_time": iqr_time,
                                                  "conn_rate": conn_rate, "snap_conn": snap_conn}

    perf_tex = ["\\begin{table}[ht]",
                "\\centering",
                f"\\caption{{{args.caption}}}",
                f"\\label{{{args.label}}}",
                "\\resizebox{\\textwidth}{!}{%",
                "\\begin{tabular}{|l|l|c|c|c|c|}",
                "\\hline",
                "Dataset & Algorithm & Total Cost (med [IQR]) & 95\\% CI & Time (med [IQR]) & Conn. rate / %snap \\\\",
                "\\hline"]
    for r in rows:
        ds, algo, medc, iqrc, lo, hi, medt, iqrt, cr, sc = r
        ci_s = f"[{lo:.2f}, {hi:.2f}]" if (lo==lo and hi==hi) else "NA"
        sc_s = f"{cr:.1f}\\% / {sc:.1f}\\%" if sc==sc else f"{cr:.1f}\\% / NA"
        perf_tex.append(f"{ds} & {algo} & {medc:.2f} [{iqrc:.2f}] & {ci_s} & {medt:.2f} [{iqrt:.2f}] & {sc_s} \\\\")
    perf_tex += ["\\hline", "\\end{tabular}", "}%","\\end{table}"]

    # TABLE 2: Pairwise Wilcoxon vs CA-ALNS (per dataset, on total_travel)
    wil_tex = ["\\begin{table}[ht]","\\centering","\\caption{Pairwise vs CA-ALNS (Wilcoxon)}","\\label{tab:wilcoxon}",
               "\\begin{tabular}{|l|l|c|c|}","\\hline","Dataset & Baseline & p-value & Cliff's $\\delta$ \\\\","\\hline"]
    for ds in datasets:
        dsub = df[df.dataset==ds]
        ref = dsub[dsub.algo=="ca-alns"]["total_travel"].dropna()
        if ref.empty: continue
        for algo in algos:
            if algo=="ca-alns": continue
            base = dsub[dsub.algo==algo]["total_travel"].dropna()
            if len(base)==0: continue
            # lower is better, so test ref vs base
            try:
                stat, p = wilcoxon(ref.values, base.values, zero_method="pratt", alternative="two-sided")
            except Exception:
                p = np.nan
            delta = cliffs_delta(-ref.values, -base.values)  # sign-flip so that positive favors CA-ALNS
            wil_tex.append(f"{ds} & {algo} & {p:.3g} & {delta:.3f} \\\\")
    wil_tex += ["\\hline","\\end{tabular}","\\end{table}"]

    os.makedirs(os.path.dirname(args.out_tex), exist_ok=True)
    with open(args.out_tex, "w") as f:
        f.write("\n".join(perf_tex) + "\n\n" + "\n".join(wil_tex))

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(stats_map, f, indent=2)

if __name__ == "__main__":
    main()
