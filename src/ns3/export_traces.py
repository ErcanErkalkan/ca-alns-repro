#!/usr/bin/env python3
import argparse, glob, json, os, csv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", required=True, help="Glob for run JSONs")
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    count = 0
    for fp in glob.glob(args.glob):
        with open(fp, "r") as f:
            try:
                data = json.load(f)
            except Exception:
                continue
        # Expect 'waypoints' or similar structure; fall back to empty
        wp = data.get("waypoints", [])
        if not wp:
            # write a stub to indicate missing traces
            base = os.path.splitext(os.path.basename(fp))[0]
            outp = os.path.join(args.out_dir, f"{base}_MISSING.csv")
            with open(outp, "w", newline="") as csvf:
                w = csv.writer(csvf)
                w.writerow(["t","x","y","h","uav_id"])
            count += 1
            continue
        base = os.path.splitext(os.path.basename(fp))[0]
        outp = os.path.join(args.out_dir, f"{base}.csv")
        with open(outp, "w", newline="") as csvf:
            w = csv.writer(csvf)
            w.writerow(["t","x","y","h","uav_id"])
            for row in wp:
                # expected dict: {'t':..., 'x':..., 'y':..., 'h':..., 'uav':...}
                w.writerow([row.get("t",0), row.get("x",0), row.get("y",0), row.get("h",100), row.get("uav",0)])
        count += 1
    print("Wrote", count, "trace files to", args.out_dir)

if __name__ == "__main__":
    main()
