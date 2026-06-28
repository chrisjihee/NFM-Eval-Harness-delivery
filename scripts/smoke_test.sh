#!/bin/bash
set -euo pipefail

# Smoke test for the Open Telco lm-eval tasks.
#
# GPU is NOT required: this only verifies that the custom task definitions load
# and register correctly via lm_eval's TaskManager. No model is loaded and no
# evaluation is run.
#
# Usage:
#   bash scripts/smoke_test.sh                 # validate the three default groups
#   bash scripts/smoke_test.sh open_telco_teleqna [more_tasks...]
#
# Exit codes:
#   0  all requested tasks/groups loaded
#   1  missing virtual environment
#   3  lm_eval not installed in .venv
#   non-zero (from python)  one or more tasks failed to load

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  echo "Missing virtual environment at ${ROOT_DIR}/.venv" >&2
  exit 1
fi

source "${ROOT_DIR}/.venv/bin/activate"

if ! python -c "import lm_eval" >/dev/null 2>&1; then
  echo "lm_eval not installed in .venv. Install: uv pip install -e ./lm-evaluation-harness --no-deps" >&2
  exit 3
fi

# Default targets: GSMA-compatible groups (primary) + legacy baseline + mcgen
# diagnostics. Override by passing task/group names.
TARGETS=("$@")
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=(
    open_telco_otlite_gsma open_telco_otfull_gsma
    open_telco_otlite_lm_eval_baseline open_telco_otfull_lm_eval_baseline
    open_telco_otlite_core4_lm_eval_baseline
    open_telco_otlite_mcgen open_telco_otfull_mcgen
  )
fi

TASKS_DIR="${ROOT_DIR}/open_telco_lm_eval/tasks"

ROOT_DIR="${ROOT_DIR}" TASKS_DIR="${TASKS_DIR}" python - "${TARGETS[@]}" <<'PY'
import os
import sys

from lm_eval.tasks import TaskManager
from lm_eval.tasks._index import Kind
from lm_eval.tasks._yaml_loader import load_yaml

tasks_dir = os.environ["TASKS_DIR"]
targets = sys.argv[1:]

# Register the custom Open Telco tasks without loading any model or dataset.
tm = TaskManager(include_path=tasks_dir)
index = tm.task_index


def output_type_of(name: str) -> str:
    """Read a task's output_type from its config YAML without instantiating it.

    Instantiating a Task downloads its dataset; reading the config does not,
    so this keeps the smoke test GPU-free and offline-friendly.
    """
    entry = index.get(name)
    if entry is None or entry.yaml_path is None:
        return ""
    cfg = load_yaml(entry.yaml_path, resolve_func=False, recursive=True)
    return cfg.get("output_type", "") or ""


def subtasks_of(group_name: str) -> list:
    """Return the leaf task names declared by a group config."""
    entry = index.get(group_name)
    if entry is None or entry.yaml_path is None:
        return []
    cfg = load_yaml(entry.yaml_path, resolve_func=False, recursive=True)
    tasks = cfg.get("task", [])
    names = []
    for t in tasks:
        if isinstance(t, str):
            names.append(t)
        elif isinstance(t, dict) and "task" in t and isinstance(t["task"], str):
            names.append(t["task"])
    return names


failures = []


def check_task(name: str, indent: str = "  ") -> None:
    entry = index.get(name)
    if entry is None:
        print(f"{indent}FAIL task    {name} (not registered)")
        failures.append(name)
        return
    print(f"{indent}ok   task    {name} (output_type={output_type_of(name)})")


for target in targets:
    entry = index.get(target)
    if entry is None:
        print(f"FAIL          {target} (not registered)")
        failures.append(target)
        continue

    if entry.kind == Kind.GROUP:
        children = subtasks_of(target)
        print(f"ok   group   {target} ({len(children)} tasks)")
        if not children:
            print(f"  FAIL group   {target} (no tasks declared)")
            failures.append(target)
        for child in children:
            check_task(child)
    else:
        check_task(target, indent="")

if failures:
    print(f"\nFAILED: {len(failures)} item(s) did not load: {failures}", file=sys.stderr)
    sys.exit(1)

print("\nOK: all requested tasks/groups loaded.")
PY
