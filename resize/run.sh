#!/usr/bin/env bash
set -euo pipefail

python3 model.py --design examples/design.json --out resize_decisions.json --time_limit 30 --max_cells 0 | cat