# Resizer (Gurobi-based)

This folder contains a standalone timing-driven resizer that integrates with your existing flow without modifying any original source files. It assumes the database stores each cell's current type (master) and that cell libraries provide discrete drive-strength options (±1 step allowed per iteration).

## Goals
- Multi-objective optimization prioritizing timing first, then power.
- Batch decide ±1 size changes for cells on critical cones to reduce the number of STA runs.
- Consume OpenROAD timing reports to extract critical endpoints and edges.

## Inputs
- `examples/design.json`: structure of the placement/timing graph subset to optimize.
  - cells: id, current_type, up_type, down_type, anchors (optional), region (optional)
  - vt_options (per cell): list of { name, d_add, P_add } specifying VT choices. d_add/P_add are linear deltas added to the size-based delay/power of that cell.
  - timing_nodes: list of node ids
  - crit_edges: list of {u, v, d_wire}
  - endpoints: list of node ids with setup requirements
  - clocks: Tclk per clock domain
  - setup: per-endpoint setup time
  - power: P_cur/P_up/P_down per cell
  - delay: d_cur/d_up/d_down per cell at current load
- `examples/report.rpt` (optional): OpenROAD timing report used by the parser.

Note: The current project data structures may not store `cell type` yet. This resizer assumes that information exists; please provide it when generating `design.json`.

## Outputs
- `resize_decisions.json`: mapping from cell id to action {stay|up|down} and resulting type.

## Usage
1. Create a Python venv and install dependencies:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. (Optional) Parse OpenROAD report to build crit edges/endpoints JSON you can merge into your design input:
```
python parse_openroad_report.py --report examples/report.rpt --out examples/crit.json
```
3. Run the resizer:
```
python model.py --design examples/design.json --out resize_decisions.json --time_limit 60 --max_cells 500
```

## Notes
- The model enforces ±1 step only for each cell per iteration.
- VT assignment is modeled as a one-hot choice per cell with additive delay/power deltas. Provide realistic `d_add`/`P_add` values (can be endpoint/RC dependent approximations refreshed each STA iteration).
- Timing constraints are applied to a subset (critical cone) to control problem size.
- Gate delay and power are linearized by per-cell deltas at current operating point; refresh them each STA iteration.
- Multi-objective is lexicographic: timing (sum of endpoint slack deficits) has higher priority than power.