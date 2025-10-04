
# CA-ALNS (Patched, Manuscript-Complete)

This patched tree aligns the implementation with the manuscript:
- Operator set: random, chain (Shaw), proximity/relatedness, worst-cost, cross-route swap/reassign
- Repair: cheapest-feasible, k-regret (k in {2,3})
- Rally-Point assistance & dwell sync
- Connectivity: tightened (R-ρ) + BFS fallback; **Option A** SINR with LoS/NLoS + interference modes
- Cadence bound: Δτ ≤ (R − 2ρ) / (2 v_max)
- ALNS+LS: 2-opt & Or-opt
- Fairness: EvalCounter (E_max), unified penalty calibration for GA/DE via upper bounds
- ns-3: waypoint export + aggregator for PDR/Delay/Hop
- Energy: RAPL reader, IPkWh metrics
- Analysis: bootstrap CI utils, Wilcoxon + Holm–Bonferroni, Cliff's δ, A12; LaTeX table emitters
- Placeholder filler for LaTeX

## Quickstart
```
cd ca-alns-repro/src

# Run CA-ALNS with LS and range-mode
python -m experiments.run_experiment --algo ca-alns --apply_ls --mode range --E_max 100000 --seed 0 --out runs/ca_alns_s0.json

# Aggregate
python -m analysis.aggregate_results --glob "runs/*.json" --out_csv analysis/summary.csv

# Build LaTeX table
python -m analysis.stats_and_tables --runs_csv analysis/summary.csv --out_tex tables/summary.tex --caption "Run Summary" --label "tab:summary"
```

## ns-3 (external)
1) Export waypoint CSVs with `ns3/ns3_pipeline.py` (connect to your routes/snapshots).
2) Run ns-3 scenario to produce `pdr.csv`, `delay.csv`, `hops.csv`.
3) Aggregate: `python -m ns3.ns3_aggregate --log_dir ns3/logs --out_prefix analysis/ns3`.

## Notes
- GA/DE baselines have been adapted to accept `eval_counter` and `penalties`. If your original interface differs, check `baselines/*.py` adapters.
- SINR model here is a practical approximation; tune `p_los`, exponents, and interference mode to your scenario.
