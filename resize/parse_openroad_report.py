#!/usr/bin/env python3
import re
import json
from pathlib import Path
from typing import Dict, Any, List

import click

start_re = re.compile(r'^Startpoint:\s+(\S+)')
end_re = re.compile(r'^Endpoint:\s+(\S+)')
pin_re = re.compile(r'^\s*[-+]?\d+\.\d+\s+\d+\.\d+\s+[v\^]\s+(\S+)/(\S+)')
slack_re = re.compile(r'^\s*(-?\d+\.\d+)\s+slack')

@click.command()
@click.option('--report', type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True, help='OpenROAD report file')
@click.option('--out', type=click.Path(dir_okay=False, path_type=Path), required=True, help='Output JSON path')
@click.option('--max_paths', type=int, default=200, help='Limit number of violating paths to extract')
def main(report: Path, out: Path, max_paths: int):
	endpoints: List[str] = []
	crit_edges: List[Dict[str, Any]] = []
	timing_nodes: Dict[str, int] = {}

	with report.open('r') as f:
		path_pins: List[str] = []
		paths_found = 0
		for line in f:
			m = start_re.search(line)
			if m:
				path_pins = []
				continue
			m = end_re.search(line)
			if m:
				endpoints.append(m.group(1))
				continue
			m = pin_re.search(line)
			if m:
				inst, pin = m.group(1), m.group(2)
				node = f"{inst}/{pin}"
				path_pins.append(node)
				timing_nodes.setdefault(node, len(timing_nodes))
				continue
			m = slack_re.search(line)
			if m:
				slack = float(m.group(1))
				if slack < 0:
					for i in range(1, len(path_pins)):
						u = path_pins[i-1]
						v = path_pins[i]
						crit_edges.append({"u": u, "v": v, "d_wire": 0.0})
					paths_found += 1
					if paths_found >= max_paths:
						break
				path_pins = []
				continue
			# else: ignore

	design = {
		"cells": [],
		"timing_nodes": list(timing_nodes.keys()),
		"crit_edges": crit_edges,
		"endpoints": endpoints,
		"setup": {},
		"clocks": [{"name": "clk", "period": 1.0}],
	}

	with out.open('w') as fo:
		json.dump(design, fo, indent=2)
	print(f"Wrote skeleton design JSON to {out}")

if __name__ == '__main__':
	main()