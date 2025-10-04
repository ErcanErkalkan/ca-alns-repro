
import pandas as pd
from pathlib import Path

def aggregate_ns3(log_dir: str, out_prefix: str):
    """Aggregate PDR/delay/hop CSVs into mission-level stats.
    Expects files:
      - pdr.csv: columns [src,dst,pdr_percent]
      - delay.csv: columns [src,dst,delay_ms]
      - hops.csv: columns [src,dst,hops]
    """
    log_dir = Path(log_dir)
    out_dir = Path(out_prefix).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    pdr = pd.read_csv(log_dir / "pdr.csv")
    delay = pd.read_csv(log_dir / "delay.csv")
    hops = pd.read_csv(log_dir / "hops.csv")
    # Summaries
    pdr_mean = pdr["pdr_percent"].mean()
    pdr_p5 = pdr["pdr_percent"].quantile(0.05)
    d_mean = delay["delay_ms"].mean()
    d_p95 = delay["delay_ms"].quantile(0.95)
    h_p50 = hops["hops"].quantile(0.50)
    h_p95 = hops["hops"].quantile(0.95)

    js = dict(PDR_mean=pdr_mean, PDR_5pct=pdr_p5, Delay_mean_ms=d_mean, Delay_95pct_ms=d_p95,
              Hop_50pct=h_p50, Hop_95pct=h_p95)
    with open(out_prefix + "_ns3_summary.json", "w") as f:
        import json; json.dump(js, f, indent=2)
    return js

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--log_dir", required=True)
    p.add_argument("--out_prefix", required=True)
    a = p.parse_args()
    s = aggregate_ns3(a.log_dir, a.out_prefix)
    print(s)
