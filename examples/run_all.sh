#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXAMPLES="$(cd "$(dirname "$0")" && pwd)"

run() {
    local dir="$1"
    local script="$2"
    echo ">>> examples/$dir/$script"
    (cd "$EXAMPLES/$dir" && python "$script")
}

# 3D experiment
run 3d_experiment run.py
run 3d_experiment plot.py

# Gill case study
run case_studies/gill run.py
run case_studies/gill plot.py

# Delay comparison
run case_studies/delay_comparison/simulator run.py
run case_studies/delay_comparison/simulator plot.py

# Network case study
run case_studies/network run.py
run case_studies/network plot.py

# SST case study
run case_studies/sst run.py
(cd "$EXAMPLES/case_studies/sst" && python analyzer.py \
    -d output_sim_3x3_2 output_sim_3x3_10 output_sim_3x3_30 output_sim_3x3_50 \
    -x 0.05 0.1 0.25 0.42 0.63 0.83 \
    -c 2 10 30 50)

# Trace example
run trace plot.py

# Interactive timeseries plotter (saves to PDF, no GUI needed)
run plotters/interactive_timeseries_plot run.py
