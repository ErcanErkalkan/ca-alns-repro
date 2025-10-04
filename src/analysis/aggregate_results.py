
import json, numpy as np, pandas as pd
from pathlib import Path

def bootstrap_ci(x, it=10000, alpha=0.05, func=np.median, rng=None):
    rng = np.random.default_rng() if rng is None else rng
    x = np.asarray(x)
    bs = [func(rng.choice(x, size=len(x), replace=True)) for _ in range(it)]
    return np.percentile(bs, [100*alpha/2, 100*(1-alpha/2)])

def summarize_runs(files):
    rows = []
    for fp in files:
        try:
            js = json.loads(Path(fp).read_text())
            cfg = js.get("config", {})
            rows.append(dict(file=fp, algo=js.get("algo","unknown"), seed=js.get("seed"),
                             R=cfg.get("connectivity",{}).get("R"),
                             mode=cfg.get("connectivity",{}).get("mode"),
                             apply_ls=cfg.get("operators",{}).get("apply_local_search"),
                             k_regret=cfg.get("operators",{}).get("k_regret"),
                             ))
        except Exception:
            pass
    df = pd.DataFrame(rows)
    return df

if __name__ == "__main__":
    import argparse, glob
    p = argparse.ArgumentParser()
    p.add_argument("--glob", default="runs/*.json")
    p.add_argument("--out_csv", default="analysis/summary.csv")
    a = p.parse_args()
    files = glob.glob(a.glob)
    df = summarize_runs(files)
    Path(a.out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out_csv, index=False)
    print("Wrote", a.out_csv, "rows:", len(df))


def improvement_per_kwh(J_ref: float, J_alg: float, E_wh: float) -> float:
    if E_wh <= 0: 
        return float('inf') if J_alg < J_ref else 0.0
    return (100.0 * (J_ref - J_alg) / max(J_ref, 1e-9)) / (E_wh / 1000.0)

def improvement_abs_per_kwh(J_ref: float, J_alg: float, E_wh: float) -> float:
    if E_wh <= 0: 
        return float('inf') if J_alg < J_ref else 0.0
    return (J_ref - J_alg) / (E_wh / 1000.0)
