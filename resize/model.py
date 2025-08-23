#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import click
import orjson

try:
	import gurobipy as gp
	from gurobipy import GRB
except Exception as e:
	print("gurobipy is not available in this environment. Please install and ensure a valid license.")
	raise


# -----------------------------
# Data loading
# -----------------------------

def load_json(path: Path) -> Any:
	with path.open('rb') as f:
		return orjson.loads(f.read())


# -----------------------------
# Model construction
# -----------------------------

def build_and_solve(design: Dict[str, Any], out_path: Path, time_limit: int, max_cells: int) -> Dict[str, Any]:
	cells: List[Dict[str, Any]] = design["cells"]
	crit_edges: List[Dict[str, Any]] = design["crit_edges"]
	timing_nodes: List[str] = design["timing_nodes"]
	endpoints: List[str] = design["endpoints"]
	setup: Dict[str, float] = design.get("setup", {})
	Tclk: float = float(design["clocks"][0]["period"]) if design.get("clocks") else float(design.get("Tclk", 1.0))

	# Optional: restrict to top-N cells in critical cone to control size
	if max_cells > 0 and len(cells) > max_cells:
		# Keep cells that appear on crit edges first
		crit_cell_ids = set()
		for e in crit_edges:
			crit_cell_ids.add(e.get("driver_cell", ""))
			crit_cell_ids.add(e.get("sink_cell", ""))
		crit_cells = [c for c in cells if c.get("id") in crit_cell_ids]
		other_cells = [c for c in cells if c.get("id") not in crit_cell_ids]
		cells = (crit_cells + other_cells)[:max_cells]

	cell_index = {c["id"]: idx for idx, c in enumerate(cells)}

	m = gp.Model("timing_first_power_second")
	if time_limit:
		m.Params.TimeLimit = time_limit
	m.Params.MIPFocus = 1
	m.Params.OutputFlag = 1

	# Variables: per-cell move
	u: Dict[str, gp.Var] = {}
	d: Dict[str, gp.Var] = {}
	s: Dict[str, gp.Var] = {}
	for c in cells:
		cid = c["id"]
		u[cid] = m.addVar(vtype=GRB.BINARY, name=f"up_{cid}")
		d[cid] = m.addVar(vtype=GRB.BINARY, name=f"down_{cid}")
		s[cid] = m.addVar(vtype=GRB.BINARY, name=f"stay_{cid}")
	m.update()
	for c in cells:
		cid = c["id"]
		m.addConstr(u[cid] + d[cid] + s[cid] == 1, name=f"one_move_{cid}")
		# Boundary guards (optional)
		if not c.get("up_type"):
			m.addConstr(u[cid] == 0, name=f"no_up_{cid}")
		if not c.get("down_type"):
			m.addConstr(d[cid] == 0, name=f"no_down_{cid}")

	# Timing variables
	T: Dict[str, gp.Var] = {v: m.addVar(lb=0.0, name=f"T_{v}") for v in timing_nodes}
	sdef: Dict[str, gp.Var] = {e: m.addVar(lb=0.0, name=f"sdef_{e}") for e in endpoints}
	m.update()

	# Linearized gate delay and power using ±1 deltas
	d_gate: Dict[str, gp.LinExpr] = {}
	P_cell: Dict[str, gp.LinExpr] = {}
	for c in cells:
		cid = c["id"]
		P_cur = float(c["power"]["P_cur"]) if c.get("power") else 0.0
		P_up = float(c["power"].get("P_up", P_cur)) if c.get("power") else P_cur
		P_down = float(c["power"].get("P_down", P_cur)) if c.get("power") else P_cur

		d_cur = float(c["delay"]["d_cur"]) if c.get("delay") else 0.0
		d_up = float(c["delay"].get("d_up", d_cur)) if c.get("delay") else d_cur
		d_down = float(c["delay"].get("d_down", d_cur)) if c.get("delay") else d_cur

		P_cell[cid] = (P_cur
					 + (P_up - P_cur) * u[cid]
					 + (P_down - P_cur) * d[cid])
		d_gate[cid] = (d_cur
					 + (d_up - d_cur) * u[cid]
					 + (d_down - d_cur) * d[cid])

	# Edge timing constraints only on critical edges
	for e in crit_edges:
		u_node = e["u"]
		v_node = e["v"]
		driver_cell = e.get("driver_cell")
		if driver_cell is None:
			# Skip if mapping is missing (user will add in real integration)
				continue
		d_wire = float(e.get("d_wire", 0.0))
		m.addConstr(T[v_node] >= T[u_node] + d_gate[driver_cell] + d_wire, name=f"edge_{u_node}_{v_node}")

	# Endpoint timing slack deficits
	for ept in endpoints:
		setup_e = float(setup.get(ept, 0.0))
		m.addConstr(sdef[ept] >= T[ept] - (Tclk - setup_e), name=f"sdef_{ept}")

	# Multi-objective: 1) timing violation; 2) total power
	timing_violation = gp.quicksum(sdef[e] for e in endpoints)
	total_power = gp.quicksum(P_cell[c["id"]] for c in cells)
	m.ModelSense = GRB.MINIMIZE
	m.setObjectiveN(timing_violation, index=0, priority=2, name="timing")
	m.setObjectiveN(total_power,      index=1, priority=1, name="power")

	m.optimize()

	# Collect results
	decisions: Dict[str, Dict[str, Any]] = {}
	for c in cells:
		cid = c["id"]
		move = "stay"
		if u[cid].X > 0.5:
			move = "up"
		elif d[cid].X > 0.5:
			move = "down"
		res_type = c.get("current_type")
		if move == "up" and c.get("up_type"):
			res_type = c["up_type"]
		elif move == "down" and c.get("down_type"):
			res_type = c["down_type"]
		decisions[cid] = {"action": move, "result_type": res_type}

	out = {"decisions": decisions,
			"obj": {"timing": float(timing_violation.getValue() if m.SolCount else math.inf),
					"power": float(total_power.getValue() if m.SolCount else math.inf)},
			"status": m.Status}

	with out_path.open('w') as f:
		json.dump(out, f, indent=2)
	return out


# -----------------------------
# CLI
# -----------------------------

@click.command()
@click.option('--design', type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True, help='Design JSON path')
@click.option('--out', type=click.Path(dir_okay=False, path_type=Path), default=Path('resize_decisions.json'), help='Output JSON for decisions')
@click.option('--time_limit', type=int, default=60, help='Time limit (seconds)')
@click.option('--max_cells', type=int, default=0, help='Limit number of cells (0=no limit)')
def main(design: Path, out: Path, time_limit: int, max_cells: int):
	design_data = load_json(design)
	res = build_and_solve(design_data, out, time_limit, max_cells)
	print(f"Status: {res['status']}")
	print(f"Timing objective: {res['obj']['timing']}")
	print(f"Power objective: {res['obj']['power']}")
	print(f"Decisions written to: {out}")


if __name__ == '__main__':
	main()