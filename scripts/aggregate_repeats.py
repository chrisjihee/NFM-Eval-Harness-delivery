#!/usr/bin/env python3
"""Aggregate N repeated GSMA-profile runs of one (model, profile) into mean ± spread.

The handoff reports each (model × profile) as the average of 3 identical runs, to
absorb run-to-run drift (vLLM batching / FP nondeterminism). This script reads the
per-run lm-eval result JSONs, extracts the 7-task **unweighted** GSMA score per run
(reusing ``compare_gsma_leaderboard``'s extraction so the numbers cannot diverge),
then reports:

* per-run unweighted task mean (mean of the 7 GSMA columns present),
* across-run **mean ± sample-std (n-1)** with min/max and explicit ``n_actual``,
* per-task mean/std across runs.

Spread rules (honest reporting of partial / deterministic trios):
* n_actual == 1 -> value only, ``spread_note = "single run, no spread"``
* n_actual == 2 -> mean + ``spread_note = "2 of 3, spread=|Δ|"``
* n_actual >= 3 -> mean ± sample std
* if std == 0 -> ``spread_note = "deterministic across repeats"``

Usage:
    python scripts/aggregate_repeats.py --label otlite-gsma-gemma3-4b \\
        results/final/otlite-gsma-gemma3-4b/run1 \\
        results/final/otlite-gsma-gemma3-4b/run2 \\
        results/final/otlite-gsma-gemma3-4b/run3 \\
        --out-json results/final/otlite-gsma-gemma3-4b/_aggregate.json

Each positional RESULT may be a ``results_*.json`` file OR a directory under which
``**/results_*.json`` is globbed (the newest match per directory is used).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any, Optional

# Reuse the compare tool's extraction so per-task/unweighted math never drifts.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare_gsma_leaderboard as cmp  # noqa: E402


def _resolve_result_json(path: Path) -> Optional[Path]:
    """A results_*.json file, or the newest such file under a directory."""
    if path.is_file():
        return path
    if path.is_dir():
        candidates = sorted(path.glob("**/results_*.json"))
        return candidates[-1] if candidates else None
    return None


def _per_run_scores(result_json: Path) -> dict[str, Any]:
    """Per-task GSMA acc + unweighted task mean for one run JSON."""
    local = cmp.load_local_result(result_json)
    track = cmp.detect_track(local)  # "otlite" | "otfull"
    mapping = cmp.get_mapping(track, profile="gsma")
    scores = cmp.extract_local_scores(local, mapping)  # public_col -> acc|None
    present = [v for v in scores.values() if isinstance(v, (int, float))]
    unweighted = statistics.fmean(present) if present else None
    missing = [c for c, v in scores.items() if not isinstance(v, (int, float))]
    return {
        "path": str(result_json),
        "track": track,
        "tasks": scores,
        "unweighted_mean": unweighted,
        "missing_tasks": missing,
    }


def _spread(values: list[float]) -> dict[str, Any]:
    n = len(values)
    if n == 0:
        return {"mean": None, "std": None, "min": None, "max": None,
                "n_actual": 0, "spread_note": "no runs"}
    mean = statistics.fmean(values)
    lo, hi = min(values), max(values)
    if n == 1:
        return {"mean": mean, "std": None, "min": lo, "max": hi,
                "n_actual": 1, "spread_note": "single run, no spread"}
    if n == 2:
        return {"mean": mean, "std": None, "min": lo, "max": hi,
                "n_actual": 2, "spread_note": f"2 of 3, spread=|Δ|={hi - lo:.4f}"}
    std = statistics.stdev(values)  # sample std (n-1)
    note = "deterministic across repeats" if std == 0 else f"{n} of 3"
    return {"mean": mean, "std": std, "min": lo, "max": hi,
            "n_actual": n, "spread_note": note}


def aggregate(label: str, result_paths: list[Path]) -> dict[str, Any]:
    resolved: list[Path] = []
    for p in result_paths:
        rj = _resolve_result_json(p)
        if rj is None:
            print(f"WARN: no results_*.json under {p}", file=sys.stderr)
            continue
        resolved.append(rj)

    runs = [_per_run_scores(rj) for rj in resolved]
    run_means = [r["unweighted_mean"] for r in runs
                 if isinstance(r["unweighted_mean"], (int, float))]
    overall = _spread(run_means)

    # Per-task aggregation across runs.
    cols = list(cmp.PUBLIC_COLUMN_ORDER)
    per_task: dict[str, Any] = {}
    for col in cols:
        vals = [r["tasks"].get(col) for r in runs]
        vals = [v for v in vals if isinstance(v, (int, float))]
        if not vals:
            per_task[col] = {"mean": None, "std": None, "n": 0, "values": []}
            continue
        per_task[col] = {
            "mean": statistics.fmean(vals),
            "std": statistics.stdev(vals) if len(vals) >= 2 else None,
            "n": len(vals),
            "values": vals,
        }

    track = runs[0]["track"] if runs else None
    return {
        "label": label,
        "track": track,
        "n_planned": 3,
        "n_actual": overall["n_actual"],
        "overall": overall,
        "per_task": per_task,
        "per_run": runs,
    }


def to_markdown(agg: dict[str, Any]) -> str:
    o = agg["overall"]
    mean = "—" if o["mean"] is None else f"{o['mean']:.4f}"
    if o["std"] is not None:
        spread = f"±{o['std']:.4f}"
    elif o["n_actual"] == 2:
        spread = o["spread_note"].split("=", 1)[-1]
    else:
        spread = o["spread_note"]
    lines = [
        f"### {agg['label']}  (track={agg['track']}, n={agg['n_actual']}/3)",
        "",
        f"**Unweighted 7-task mean: {mean} {spread}**  ({o['spread_note']})",
        "",
        "| task | mean | n |",
        "|---|---:|---:|",
    ]
    for col, t in agg["per_task"].items():
        m = "—" if t["mean"] is None else f"{t['mean']:.4f}"
        lines.append(f"| {col} | {m} | {t['n']} |")
    lines.append("")
    lines.append("Per-run unweighted means: " + ", ".join(
        f"{r['unweighted_mean']:.4f}" if isinstance(r["unweighted_mean"], (int, float))
        else "—" for r in agg["per_run"]))
    return "\n".join(lines)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", nargs="+",
                    help="results_*.json files or run directories (3 expected)")
    ap.add_argument("--label", required=True, help="e.g. otlite-gsma-gemma3-4b")
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=None)
    return ap.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    agg = aggregate(args.label, [Path(p) for p in args.results])
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(agg, indent=2, ensure_ascii=False))
    md = to_markdown(agg)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(md + "\n")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
