# Repro Makefile (Windows/POSIX)

PY ?= python
SRC := $(CURDIR)/src
export PYTHONPATH := $(SRC):$(PYTHONPATH)

RUNS ?= runs
RESULTS ?= results
FIGS ?= figs
NS3_TRACES ?= ns3_traces
NS3_LOGS ?= ns3_logs

# Scales & algs
SCALES ?= Small Medium Large
ALGS ?= de ga alns-std alns-ls ca-alns
# Windows'ta seq yok; run_grid varsayılan 0..29 seed kullanır.

# Fairness budgets
E_MAX ?= 100000
T_MAX ?= 600

# Scale->(n_uav n_targets)
SMALL_UAV ?= 5
SMALL_TGT ?= 20
MEDIUM_UAV ?= 10
MEDIUM_TGT ?= 50
LARGE_UAV ?= 20
LARGE_TGT ?= 100
XL_UAV ?= 50
XL_TGT ?= 1000

# Figures flags
DO_CONVERGENCE ?= 1
DO_EVAL_PROFILE ?= 1
DO_SCALING ?= 1

.PHONY: all runs aggregate stats plots ns3 ns3-export ns3-aggregate ns3-plots fill-tex clean

all: runs aggregate stats plots

runs:
	@$(PY) scripts/run_grid.py \
	  --runs_root "$(RUNS)" \
	  --e_max $(E_MAX) --t_max $(T_MAX) \
	  --scales $(SCALES) \
	  --algs $(ALGS) \
	  --small $(SMALL_UAV) $(SMALL_TGT) \
	  --medium $(MEDIUM_UAV) $(MEDIUM_TGT) \
	  --large $(LARGE_UAV) $(LARGE_TGT) \
	  --xl $(XL_UAV) $(XL_TGT)

aggregate:
	@$(PY) -c "import os; os.makedirs('$(RESULTS)', exist_ok=True)"
	@$(PY) scripts/aggregate_results.py \
	  --glob "$(RUNS)/**/seed_*.json" \
	  --out_csv "$(RESULTS)/runs.csv"

stats:
	@$(PY) scripts/make_tables.py \
	  --runs_csv "$(RESULTS)/runs.csv" \
	  --out_tex "$(RESULTS)/tables.tex" \
	  --out_json "$(RESULTS)/tables.json" \
	  --caption "Performance and connectivity statistics" \
	  --label "tab:main_results"

plots:
ifeq ($(DO_CONVERGENCE),1)
	@$(PY) -m plots.convergence \
	  --agg "$(RESULTS)/runs.csv" \
	  --out "$(FIGS)/convergence.png"
endif
ifeq ($(DO_EVAL_PROFILE),1)
	@$(PY) scripts/plot_eval_profile.py \
	  --agg "$(RESULTS)/runs.csv" \
	  --out "$(FIGS)/eval_profile.png"
endif
ifeq ($(DO_SCALING),1)
	@$(PY) scripts/plot_scaling.py \
	  --agg "$(RESULTS)/runs.csv" \
	  --out "$(FIGS)/scaling.png"
endif

ns3: ns3-export ns3-aggregate ns3-plots

# Export traces for ns-3
# Usage: make ns3-export SCALE=Medium ALGO=ca-alns
SCALE ?= Medium
ALGO ?= ca-alns
ns3-export:
	@$(PY) -m ns3.export_traces \
	  --glob "$(RUNS)/$(SCALE)/$(ALGO)/seed_*.json" \
	  --out_dir "$(NS3_TRACES)/$(SCALE)"

# Aggregate ns-3 logs -> results/ns3_$(SCALE).csv
ns3-aggregate:
	@$(PY) -m ns3.ns3_aggregate \
	  --logs "$(NS3_LOGS)/$(SCALE)" \
	  --out "$(RESULTS)/ns3_$(SCALE).csv"

# Plot PDR heatmap / delay CDF / hop CDF
ns3-plots:
	@$(PY) -m plots.pdr_heatmap \
	  --csv "$(RESULTS)/ns3_$(SCALE).csv" \
	  --out "$(FIGS)/pdr_heatmap_$(SCALE).png"
	@$(PY) -m plots.delay_cdf \
	  --csv "$(RESULTS)/ns3_$(SCALE).csv" \
	  --out "$(FIGS)/delay_cdf_$(SCALE).png"
	@$(PY) -m plots.hop_cdf \
	  --csv "$(RESULTS)/ns3_$(SCALE).csv" \
	  --out "$(FIGS)/hop_cdf_$(SCALE).png"

# Fill LaTeX placeholders in TEX using results/tables.json
# Usage: make fill-tex TEX=paper/main.tex OUT=paper/main_filled.tex
TEX ?= paper/main.tex
OUT ?= paper/main_filled.tex
fill-tex:
	@$(PY) -m analysis.fill_placeholders \
	  --tex "$(TEX)" \
	  --mapping "$(RESULTS)/tables.json" \
	  --out "$(OUT)"

clean:
	@$(PY) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in [r'$(RUNS)', r'$(RESULTS)', r'$(FIGS)', r'$(NS3_TRACES)', r'$(NS3_LOGS)']]"
