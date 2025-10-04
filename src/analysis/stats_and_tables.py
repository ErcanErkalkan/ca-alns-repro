
import numpy as np, pandas as pd, json
from pathlib import Path
from math import isfinite

def wilcoxon_signed_rank(x, y):
    from scipy.stats import wilcoxon
    return wilcoxon(x, y, zero_method='wilcox', correction=False, alternative='two-sided', mode='auto')

def holm_bonferroni(p_vals):
    m = len(p_vals)
    order = np.argsort(p_vals)
    adj = np.zeros(m)
    for rank, idx in enumerate(order):
        adj[idx] = min(1.0, p_vals[idx] * (m - rank))
    return adj

def cliffs_delta(x, y):
    # Returns delta and A12
    x = np.asarray(x); y = np.asarray(y)
    n1 = len(x); n2 = len(y)
    count = 0
    for xi in x:
        count += np.sum(xi > y) - np.sum(xi < y)
    delta = count / (n1*n2)
    A12 = (delta + 1.0)/2.0
    return float(delta), float(A12)

def latex_table_from_runs(runs_csv: str, out_tex: str, caption: str, label: str):
    df = pd.read_csv(runs_csv)
    # This is a scaffold; users can join real metrics columns.
    cols = [c for c in df.columns if c not in ["file"]]
    lines = ["\\begin{table}[ht]", "\\centering", f"\\caption{{{caption}}}", f"\\label{{{label}}}",
             "\\begin{tabular}{"+("l"*(len(cols)+1))+"}", "\\toprule"]
    lines.append("file & " + " & ".join(cols) + " \\ \\midrule")
    for _, row in df.iterrows():
        vals = [str(row[c]) for c in cols]
        lines.append(str(row['file']) + " & " + " & ".join(vals) + " \\")
    lines.append("\\bottomrule\n\\end{tabular}\n\\end{table}")
    Path(out_tex).write_text("\n".join(lines), encoding="utf-8")
    return out_tex

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--runs_csv", required=True)
    p.add_argument("--out_tex", required=True)
    p.add_argument("--caption", default="Summary")
    p.add_argument("--label", default="tab:summary")
    a = p.parse_args()
    t = latex_table_from_runs(a.runs_csv, a.out_tex, a.caption, a.label)
    print("Wrote", t)
