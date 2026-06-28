#!/usr/bin/env python3
"""Compare a local lm-eval result against the public GSMA Open Telco leaderboard.

This tool reads a local LM-Evaluation-Harness result JSON -- a leaderboard-comparable
``open_telco_otlite_gsma`` / ``open_telco_otfull_gsma`` run (use ``--profile gsma``),
or a legacy diagnostic ``*_lm_eval_baseline`` run (default profile) -- extracts the
per-task primary accuracy (``acc,none``) and the group score, then aligns those numbers
task-wise with a public row from the ``GSMA/leaderboard`` dataset.

It DOES NOT hardcode any score. Public values are loaded from the ``datasets`` library;
the only manual fallback is an optional public JSON file you supply yourself.

The output is a per-task delta table (public, local, delta = local - public) plus two
aggregate views that are NOT the same thing:

* local group acc (sample-weighted) -- the group value already stored in the result JSON.
* local unweighted task mean -- the simple mean of the 7 task accuracies. This is the
  apples-to-apples comparison against the public average, which is itself an unweighted mean.

Two profiles are available via ``--profile``:

* ``gsma`` (RECOMMENDED for leaderboard comparison) maps public columns to the
  ``*_mcgen`` / ``*_gsma`` tasks (groups ``open_telco_{otlite,otfull}_gsma``), emits the
  per-task delta table FIRST, labels the single average as a leaderboard convention NOT
  computed by official GSMA code, and annotates the 4 MC rows whose generation engine is
  UNALIGNED with the official constrained decoding. A generation-vs-constrained-decoding
  sensitivity view, NOT a reproduction.
* ``default`` maps public columns to the renamed legacy ``*_lm_eval_baseline``
  (loglikelihood) tasks. Diagnostic only -- NOT leaderboard-comparable. For historical
  pre-rename result JSONs (bare task names), add ``--map public_col=old_task`` overrides.

Usage examples
--------------

Load the public row from the GSMA dataset (requires network) and compare:

    python scripts/compare_gsma_leaderboard.py \\
        --profile gsma \\
        --local-result results/open_telco_otlite_gsma/google__gemma-3-4b-it/<results>.json \\
        --model gemma3-4b

Offline / no network -- supply the public row yourself via a JSON file:

    python scripts/compare_gsma_leaderboard.py \\
        --profile gsma \\
        --local-result results/open_telco_otlite_gsma/google__gemma-3-4b-it/<results>.json \\
        --model gemma3-4b \\
        --public-json my_public_row.json

Save Markdown and CSV in addition to stdout:

    python scripts/compare_gsma_leaderboard.py \\
        --local-result <local.json> \\
        --model gemma3-4b \\
        --out-md compare.md \\
        --out-csv compare.csv

Fallback public JSON format
---------------------------

A flat mapping of public column -> score (and optional ``average``):

    {
        "teleqna": 0.652333,
        "teletables": 0.273333,
        "oranbench": 0.66,
        "srsranbench": 0.74,
        "telemath": 0.136667,
        "telelogs": 0.116667,
        "three_gpp": 0.2,
        "average": 0.397
    }

Each value may also be a ``[score, stderr]`` pair (the native leaderboard cell format),
in which case the first element is used as the score.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Public leaderboard column -> local task name, per benchmark track.
# Keys are the public GSMA/leaderboard benchmark columns; values are the local
# lm-eval task names for that track.
# Default ("lm_eval_baseline") profile -> the renamed legacy loglikelihood tasks.
# These are diagnostic only and NOT leaderboard-comparable (use --profile gsma).
# NOTE: historical pre-rename result JSONs used the bare names (e.g.
# ``open_telco_teleqna``); for those, pass --map public_col=old_task overrides.
MAPPING_OT_LITE: dict[str, str] = {
    "teleqna": "open_telco_teleqna_lm_eval_baseline",
    "teletables": "open_telco_teletables_lm_eval_baseline",
    "oranbench": "open_telco_oranbench_lm_eval_baseline",
    "srsranbench": "open_telco_srsranbench_lm_eval_baseline",
    "telemath": "open_telco_telemath_lm_eval_baseline",
    "telelogs": "open_telco_telelogs_lm_eval_baseline",
    "three_gpp": "open_telco_3gpp_tsg_gen_lm_eval_baseline",
}

MAPPING_OT_FULL: dict[str, str] = {
    "teleqna": "open_telco_full_teleqna_lm_eval_baseline",
    "teletables": "open_telco_full_teletables_lm_eval_baseline",
    "oranbench": "open_telco_full_oranbench_lm_eval_baseline",
    "srsranbench": "open_telco_full_srsranbench_lm_eval_baseline",
    "telemath": "open_telco_full_telemath_lm_eval_baseline",
    "telelogs": "open_telco_full_telelogs_lm_eval_baseline",
    "three_gpp": "open_telco_full_3gpp_tsg_lm_eval_baseline",
}

# GSMA-aligned (non-default) profile mappings. These point at the additive
# *_mcgen (generation-based MC) and *_gsma (generation scorer) local tasks
# instead of the frozen default multiple_choice / generate tasks. The MC rows
# (teleqna/teletables/oranbench/srsranbench) use a generation engine that is
# UNALIGNED with the official constrained-decoding multiple_choice path; the
# *_gsma generation rows mirror the gsma-evals scorer rules but run on a
# different generation engine (lm-eval vs Inspect). See CAVEAT_TEXT_GSMA.
MAPPING_OT_LITE_GSMA: dict[str, str] = {
    "teleqna": "open_telco_teleqna_mcgen",
    "teletables": "open_telco_teletables_mcgen",
    "oranbench": "open_telco_oranbench_mcgen",
    "srsranbench": "open_telco_srsranbench_mcgen",
    "telemath": "open_telco_telemath_gsma",
    "telelogs": "open_telco_telelogs_gsma",
    "three_gpp": "open_telco_3gpp_tsg_gsma",
}

MAPPING_OT_FULL_GSMA: dict[str, str] = {
    "teleqna": "open_telco_full_teleqna_mcgen",
    "teletables": "open_telco_full_teletables_mcgen",
    "oranbench": "open_telco_full_oranbench_mcgen",
    "srsranbench": "open_telco_full_srsranbench_mcgen",
    "telemath": "open_telco_full_telemath_gsma",
    "telelogs": "open_telco_full_telelogs_gsma",
    "three_gpp": "open_telco_full_3gpp_tsg_gsma",
}

# Public columns whose GSMA-profile local tasks use the UNALIGNED free-generation
# MC engine (vs the official constrained-decoding multiple_choice path).
MC_ENGINE_UNALIGNED_COLUMNS = frozenset(
    {"teleqna", "teletables", "oranbench", "srsranbench"}
)

# Group names that hold the sample-weighted aggregate in the result JSON, by track.
GROUP_NAME_OT_LITE = "open_telco_otlite_lm_eval_baseline"
GROUP_NAME_OT_FULL = "open_telco_otfull_lm_eval_baseline"

# Non-default GSMA-aligned group names (unweighted task mean).
GROUP_NAME_OT_LITE_GSMA = "open_telco_otlite_gsma"
GROUP_NAME_OT_FULL_GSMA = "open_telco_otfull_gsma"

PRIMARY_METRIC = "acc,none"

# Public column order used for stable output.
PUBLIC_COLUMN_ORDER = [
    "teleqna",
    "teletables",
    "oranbench",
    "srsranbench",
    "telemath",
    "telelogs",
    "three_gpp",
]

CAVEAT_TEXT = (
    "CAVEAT:\n"
    "- public avg is an UNWEIGHTED task mean, while the local group acc is "
    "SAMPLE-WEIGHTED. The honest like-for-like comparison is unweighted mean vs "
    "unweighted mean.\n"
    "- The exact official GSMA extraction method and the public model variant are "
    "UNKNOWN, so each delta is a candidate gap, not a definitive conclusion.\n"
    "- ot-lite uses a different split from ot-full / the public leaderboard; be "
    "careful comparing ot-lite directly against leaderboard numbers."
)

CAVEAT_TEXT_GSMA = (
    "CAVEAT (gsma profile):\n"
    "- For the 4 MC tasks (teleqna/teletables/oranbench/srsranbench) the engine -- "
    "official multiple_choice(cot=False)+choice() constrained decoding vs lm-eval "
    "generate_until + until:[\\n] + max_gen_toks:8 free single-letter generation -- "
    "is the LARGEST UNALIGNED axis and the dominant candidate-gap driver; the MC "
    "delta primarily measures generation-vs-constrained-decoding sensitivity, NEVER "
    "official reproduction.\n"
    "- The *_gsma generation scorer rules mirror the gsma-evals source, but the "
    "generation engine differs (lm-eval generate vs Inspect generate).\n"
    "- The GSMA repo computes no cross-task average; the single unweighted task mean "
    "below is a leaderboard convention only, NOT computed by official GSMA code.\n"
    "- No production runtime / provider / model-revision parity is claimed."
)


class CompareError(Exception):
    """Raised for expected, user-facing failures with a clear message."""


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def load_local_result(path: Path) -> dict[str, Any]:
    """Load and minimally validate the local lm-eval result JSON."""
    if not path.exists():
        raise CompareError(f"Local result file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise CompareError(f"Local result file is not valid JSON ({path}): {exc}") from exc
    if not isinstance(data, dict) or "results" not in data:
        raise CompareError(
            f"Local result JSON missing top-level 'results' key: {path}"
        )
    return data


def detect_track(local: dict[str, Any]) -> str:
    """Detect 'ot-full' or 'ot-lite' from the result JSON task names.

    Returns 'ot-full' if any full-track task/group is present, else 'ot-lite'.
    Recognizes both default and GSMA-profile (``*_mcgen`` / ``*_gsma``) task
    names; any ot-full task name (including ``open_telco_full_*_gsma``) starts
    with ``open_telco_full_``, so the prefix check already covers them.
    """
    results = local.get("results", {})
    groups = local.get("groups", {})
    names = set(results.keys()) | set(groups.keys())
    if any(name.startswith("open_telco_full_") for name in names):
        return "ot-full"
    if GROUP_NAME_OT_FULL in names or GROUP_NAME_OT_FULL_GSMA in names:
        return "ot-full"
    return "ot-lite"


def get_mapping(track: str, profile: str = "default") -> dict[str, str]:
    if profile == "gsma":
        return MAPPING_OT_FULL_GSMA if track == "ot-full" else MAPPING_OT_LITE_GSMA
    return MAPPING_OT_FULL if track == "ot-full" else MAPPING_OT_LITE


def get_group_name(track: str, profile: str = "default") -> str:
    if profile == "gsma":
        return (
            GROUP_NAME_OT_FULL_GSMA if track == "ot-full" else GROUP_NAME_OT_LITE_GSMA
        )
    return GROUP_NAME_OT_FULL if track == "ot-full" else GROUP_NAME_OT_LITE


def parse_mapping_overrides(overrides: list[str]) -> dict[str, str]:
    """Parse --map public_col=local_task overrides into a dict."""
    parsed: dict[str, str] = {}
    for item in overrides:
        if "=" not in item:
            raise CompareError(
                f"Invalid --map entry '{item}'. Expected format public_col=local_task"
            )
        col, task = item.split("=", 1)
        col = col.strip()
        task = task.strip()
        if not col or not task:
            raise CompareError(
                f"Invalid --map entry '{item}'. Both sides must be non-empty."
            )
        parsed[col] = task
    return parsed


def extract_local_scores(
    local: dict[str, Any], mapping: dict[str, str]
) -> dict[str, Optional[float]]:
    """Extract local primary-metric acc per public column.

    Returns a mapping public_col -> acc (float) or None when the mapped task or
    metric is absent.
    """
    results = local.get("results", {})
    scores: dict[str, Optional[float]] = {}
    for col, task in mapping.items():
        entry = results.get(task)
        if not isinstance(entry, dict):
            scores[col] = None
            continue
        value = entry.get(PRIMARY_METRIC)
        scores[col] = float(value) if isinstance(value, (int, float)) else None
    return scores


def extract_local_group_acc(
    local: dict[str, Any], group_name: str
) -> Optional[float]:
    """Extract the sample-weighted group acc from groups (fallback: results)."""
    for container_key in ("groups", "results"):
        container = local.get(container_key, {})
        entry = container.get(group_name)
        if isinstance(entry, dict):
            value = entry.get(PRIMARY_METRIC)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def _coerce_score(value: Any) -> Optional[float]:
    """Coerce a public cell into a float score.

    Accepts:
    * a bare number,
    * a ``[score, stderr]`` style list/tuple,
    * a string-encoded list such as ``"[0.912, 0.0028]"`` (the native GSMA cell
      format), or a plain numeric string.
    """
    if isinstance(value, bool):  # avoid treating True/False as 1/0
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        return _coerce_score(value[0])
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # Try to parse a JSON-encoded list/number first (e.g. "[0.912, 0.0028]").
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        if parsed is not None and not isinstance(parsed, str):
            return _coerce_score(parsed)
        try:
            return float(text)
        except (TypeError, ValueError):
            return None
    return None


def load_public_from_json(
    path: Path, mapping: dict[str, str]
) -> tuple[dict[str, Optional[float]], Optional[float]]:
    """Load a public row from a manual JSON fallback file.

    Returns (per-column scores, average-or-None).
    """
    if not path.exists():
        raise CompareError(f"Public JSON file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise CompareError(f"Public JSON file is not valid JSON ({path}): {exc}") from exc
    if not isinstance(data, dict):
        raise CompareError(
            f"Public JSON must be an object mapping column->score: {path}"
        )
    scores: dict[str, Optional[float]] = {}
    for col in mapping:
        scores[col] = _coerce_score(data[col]) if col in data else None
    average = _coerce_score(data["average"]) if "average" in data else None
    return scores, average


def load_public_from_dataset(
    model: str, mapping: dict[str, str]
) -> tuple[dict[str, Optional[float]], Optional[float]]:
    """Load a public row from the GSMA/leaderboard dataset via the datasets library.

    Tries multiple configs/splits because the public layout is not guaranteed.
    Raises CompareError with a clear, actionable message on any failure.
    """
    try:
        import datasets  # type: ignore
    except ImportError as exc:
        raise CompareError(
            "The 'datasets' library is required to load the public leaderboard. "
            "Install it (pip install datasets) or pass --public-json with a manual row."
        ) from exc

    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    # Strategy 1: default load_dataset (may yield a DatasetDict of splits).
    try:
        ds = datasets.load_dataset("GSMA/leaderboard")
        rows = _collect_rows(ds)
    except Exception as exc:  # noqa: BLE001 - surface a friendly message below
        errors.append(f"load_dataset('GSMA/leaderboard'): {exc!r}")

    # Strategy 2: enumerate available configs and try each.
    if not rows:
        try:
            configs = datasets.get_dataset_config_names("GSMA/leaderboard")
        except Exception as exc:  # noqa: BLE001
            configs = []
            errors.append(f"get_dataset_config_names: {exc!r}")
        for cfg in configs:
            try:
                ds = datasets.load_dataset("GSMA/leaderboard", cfg)
                collected = _collect_rows(ds)
                if collected:
                    rows = collected
                    break
            except Exception as exc:  # noqa: BLE001
                errors.append(f"load_dataset(config={cfg!r}): {exc!r}")

    if not rows:
        detail = "\n  - ".join(errors) if errors else "no rows returned"
        raise CompareError(
            "Failed to load the public GSMA/leaderboard dataset.\n"
            f"Attempts:\n  - {detail}\n"
            "This is commonly a network/auth issue. Re-run with --public-json "
            "<path> to supply the public row manually (see file docstring for format)."
        )

    row = _find_model_row(rows, model)
    if row is None:
        available = sorted({_row_model_name(r) for r in rows if _row_model_name(r)})
        sample = ", ".join(available[:30])
        raise CompareError(
            f"Model '{model}' not found in the public leaderboard.\n"
            f"Available models (first 30): {sample}\n"
            "Use --model with an exact name, or supply --public-json."
        )

    scores: dict[str, Optional[float]] = {}
    for col in mapping:
        scores[col] = _coerce_score(row[col]) if col in row else None
    average = None
    for avg_key in ("average", "avg", "Average", "mean"):
        if avg_key in row:
            average = _coerce_score(row[avg_key])
            break
    return scores, average


def _collect_rows(ds: Any) -> list[dict[str, Any]]:
    """Flatten a Dataset or DatasetDict into a list of row dicts."""
    rows: list[dict[str, Any]] = []
    # DatasetDict: iterate over splits.
    if hasattr(ds, "keys") and hasattr(ds, "values") and not hasattr(ds, "features"):
        for split in ds.values():
            rows.extend(_dataset_to_rows(split))
        return rows
    return _dataset_to_rows(ds)


def _dataset_to_rows(split: Any) -> list[dict[str, Any]]:
    try:
        return [dict(r) for r in split]
    except Exception:  # noqa: BLE001
        return []


def _row_model_name(row: dict[str, Any]) -> Optional[str]:
    for key in ("model", "Model", "model_name", "name"):
        if key in row and row[key] is not None:
            return str(row[key])
    return None


def _find_model_row(
    rows: list[dict[str, Any]], model: str
) -> Optional[dict[str, Any]]:
    """Find the row for the requested model (exact, then case-insensitive)."""
    target = model.strip()
    for row in rows:
        if _row_model_name(row) == target:
            return row
    lowered = target.lower()
    for row in rows:
        name = _row_model_name(row)
        if name is not None and name.lower() == lowered:
            return row
    return None


def build_table(
    mapping: dict[str, str],
    public_scores: dict[str, Optional[float]],
    local_scores: dict[str, Optional[float]],
) -> list[dict[str, Any]]:
    """Build per-task rows ordered by the canonical public column order."""
    ordered_cols = [c for c in PUBLIC_COLUMN_ORDER if c in mapping]
    ordered_cols += [c for c in mapping if c not in ordered_cols]

    table: list[dict[str, Any]] = []
    for col in ordered_cols:
        pub = public_scores.get(col)
        loc = local_scores.get(col)
        delta = (loc - pub) if (pub is not None and loc is not None) else None
        table.append(
            {
                "public_column": col,
                "local_task": mapping[col],
                "public": pub,
                "local": loc,
                "delta": delta,
            }
        )
    return table


def _mean(values: list[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def compute_aggregates(
    table: list[dict[str, Any]],
    public_average: Optional[float],
    local_group_acc: Optional[float],
) -> dict[str, Optional[float]]:
    """Compute aggregate comparison values."""
    local_vals = [r["local"] for r in table if r["local"] is not None]
    public_vals = [r["public"] for r in table if r["public"] is not None]

    local_unweighted = _mean(local_vals)
    public_unweighted_computed = _mean(public_vals)

    return {
        "local_group_acc_weighted": local_group_acc,
        "local_unweighted_mean": local_unweighted,
        "public_average_reported": public_average,
        "public_unweighted_mean_computed": public_unweighted_computed,
        "delta_unweighted": (
            local_unweighted - public_unweighted_computed
            if (local_unweighted is not None and public_unweighted_computed is not None)
            else None
        ),
    }


def _fmt(value: Optional[float], digits: int = 4) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def _fmt_signed(value: Optional[float], digits: int = 4) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.{digits}f}"


def render_markdown(
    track: str,
    model: str,
    public_source: str,
    table: list[dict[str, Any]],
    aggregates: dict[str, Optional[float]],
) -> str:
    lines: list[str] = []
    lines.append(f"# GSMA leaderboard comparison: {model}")
    lines.append("")
    lines.append(f"- Track detected: `{track}`")
    lines.append(f"- Public source: {public_source}")
    lines.append(f"- Primary metric: `{PRIMARY_METRIC}`")
    lines.append("")
    lines.append("## Per-task deltas")
    lines.append("")
    lines.append("| Public column | Local task | Public | Local | Delta (local-public) |")
    lines.append("|---|---|---:|---:|---:|")
    for r in table:
        lines.append(
            f"| `{r['public_column']}` | `{r['local_task']}` | "
            f"{_fmt(r['public'])} | {_fmt(r['local'])} | {_fmt_signed(r['delta'])} |"
        )
    lines.append("")
    lines.append("## Aggregates")
    lines.append("")
    lines.append("| Aggregate | Value |")
    lines.append("|---|---:|")
    lines.append(
        f"| local group acc (sample-weighted) | "
        f"{_fmt(aggregates['local_group_acc_weighted'])} |"
    )
    lines.append(
        f"| local unweighted task mean | "
        f"{_fmt(aggregates['local_unweighted_mean'])} |"
    )
    lines.append(
        f"| public average (reported) | "
        f"{_fmt(aggregates['public_average_reported'])} |"
    )
    lines.append(
        f"| public unweighted mean (computed from tasks) | "
        f"{_fmt(aggregates['public_unweighted_mean_computed'])} |"
    )
    lines.append(
        f"| delta unweighted (local mean - public computed mean) | "
        f"{_fmt_signed(aggregates['delta_unweighted'])} |"
    )
    lines.append("")
    lines.append("## Caveat")
    lines.append("")
    for line in CAVEAT_TEXT.splitlines():
        lines.append(line)
    lines.append("")
    return "\n".join(lines)


def render_stdout(
    track: str,
    model: str,
    public_source: str,
    table: list[dict[str, Any]],
    aggregates: dict[str, Optional[float]],
) -> str:
    lines: list[str] = []
    lines.append(f"GSMA leaderboard comparison: {model}")
    lines.append(f"  track detected : {track}")
    lines.append(f"  public source  : {public_source}")
    lines.append(f"  primary metric : {PRIMARY_METRIC}")
    lines.append("")

    header = f"{'public_column':<16} {'local_task':<28} {'public':>9} {'local':>9} {'delta':>10}"
    lines.append(header)
    lines.append("-" * len(header))
    for r in table:
        lines.append(
            f"{r['public_column']:<16} {r['local_task']:<28} "
            f"{_fmt(r['public']):>9} {_fmt(r['local']):>9} {_fmt_signed(r['delta']):>10}"
        )
    lines.append("")
    lines.append("Aggregates:")
    lines.append(
        f"  local group acc (sample-weighted)            : "
        f"{_fmt(aggregates['local_group_acc_weighted'])}"
    )
    lines.append(
        f"  local unweighted task mean                   : "
        f"{_fmt(aggregates['local_unweighted_mean'])}"
    )
    lines.append(
        f"  public average (reported)                    : "
        f"{_fmt(aggregates['public_average_reported'])}"
    )
    lines.append(
        f"  public unweighted mean (computed from tasks) : "
        f"{_fmt(aggregates['public_unweighted_mean_computed'])}"
    )
    lines.append(
        f"  delta unweighted (local mean - public mean)  : "
        f"{_fmt_signed(aggregates['delta_unweighted'])}"
    )
    lines.append("")
    lines.append(CAVEAT_TEXT)
    return "\n".join(lines)


# Per-row annotation appended to the MC rows in the GSMA profile output.
MC_ROW_ANNOTATION = (
    "engine UNALIGNED (free gen vs constrained decode); dominant candidate-gap "
    "driver; measures gen-vs-constrained sensitivity"
)


def render_stdout_gsma(
    track: str,
    model: str,
    public_source: str,
    table: list[dict[str, Any]],
    aggregates: dict[str, Optional[float]],
) -> str:
    """GSMA-profile stdout: per-task delta table FIRST, then a single labeled mean.

    The per-task delta table is emitted before any aggregate, MC rows carry an
    explicit engine-unaligned annotation, and the single average is labeled as a
    leaderboard convention not computed by official GSMA code.
    """
    lines: list[str] = []
    lines.append(f"GSMA leaderboard comparison (gsma profile): {model}")
    lines.append(f"  track detected : {track}")
    lines.append(f"  public source  : {public_source}")
    lines.append(f"  primary metric : {PRIMARY_METRIC}")
    lines.append("")

    lines.append("Per-task deltas:")
    header = f"{'public_column':<16} {'local_task':<32} {'public':>9} {'local':>9} {'delta':>10}"
    lines.append(header)
    lines.append("-" * len(header))
    for r in table:
        lines.append(
            f"{r['public_column']:<16} {r['local_task']:<32} "
            f"{_fmt(r['public']):>9} {_fmt(r['local']):>9} {_fmt_signed(r['delta']):>10}"
        )
        if r["public_column"] in MC_ENGINE_UNALIGNED_COLUMNS:
            lines.append(f"  ^ {MC_ROW_ANNOTATION}")
    lines.append("")

    lines.append(
        "leaderboard-convention unweighted mean -- NOT computed by official GSMA code:"
    )
    lines.append(
        f"  local unweighted task mean                   : "
        f"{_fmt(aggregates['local_unweighted_mean'])}"
    )
    lines.append(
        f"  public unweighted mean (computed from tasks) : "
        f"{_fmt(aggregates['public_unweighted_mean_computed'])}"
    )
    lines.append(
        f"  public average (reported)                    : "
        f"{_fmt(aggregates['public_average_reported'])}"
    )
    lines.append(
        f"  delta unweighted (local mean - public mean)  : "
        f"{_fmt_signed(aggregates['delta_unweighted'])}"
    )
    lines.append(
        f"  local group acc (sample-weighted)            : "
        f"{_fmt(aggregates['local_group_acc_weighted'])}"
    )
    lines.append("")
    lines.append(CAVEAT_TEXT_GSMA)
    return "\n".join(lines)


def render_markdown_gsma(
    track: str,
    model: str,
    public_source: str,
    table: list[dict[str, Any]],
    aggregates: dict[str, Optional[float]],
) -> str:
    """GSMA-profile Markdown: per-task delta table first, then the labeled mean."""
    lines: list[str] = []
    lines.append(f"# GSMA leaderboard comparison (gsma profile): {model}")
    lines.append("")
    lines.append(f"- Track detected: `{track}`")
    lines.append(f"- Public source: {public_source}")
    lines.append(f"- Primary metric: `{PRIMARY_METRIC}`")
    lines.append("")
    lines.append("## Per-task deltas")
    lines.append("")
    lines.append(
        "| Public column | Local task | Public | Local | Delta (local-public) | Note |"
    )
    lines.append("|---|---|---:|---:|---:|---|")
    for r in table:
        note = (
            MC_ROW_ANNOTATION
            if r["public_column"] in MC_ENGINE_UNALIGNED_COLUMNS
            else ""
        )
        lines.append(
            f"| `{r['public_column']}` | `{r['local_task']}` | "
            f"{_fmt(r['public'])} | {_fmt(r['local'])} | {_fmt_signed(r['delta'])} | "
            f"{note} |"
        )
    lines.append("")
    lines.append(
        "## Leaderboard-convention unweighted mean (NOT computed by official GSMA code)"
    )
    lines.append("")
    lines.append("| Aggregate | Value |")
    lines.append("|---|---:|")
    lines.append(
        f"| local unweighted task mean | "
        f"{_fmt(aggregates['local_unweighted_mean'])} |"
    )
    lines.append(
        f"| public unweighted mean (computed from tasks) | "
        f"{_fmt(aggregates['public_unweighted_mean_computed'])} |"
    )
    lines.append(
        f"| public average (reported) | "
        f"{_fmt(aggregates['public_average_reported'])} |"
    )
    lines.append(
        f"| delta unweighted (local mean - public computed mean) | "
        f"{_fmt_signed(aggregates['delta_unweighted'])} |"
    )
    lines.append(
        f"| local group acc (sample-weighted) | "
        f"{_fmt(aggregates['local_group_acc_weighted'])} |"
    )
    lines.append("")
    lines.append("## Caveat")
    lines.append("")
    for line in CAVEAT_TEXT_GSMA.splitlines():
        lines.append(line)
    lines.append("")
    return "\n".join(lines)


def write_csv(
    path: Path,
    table: list[dict[str, Any]],
    aggregates: dict[str, Optional[float]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["public_column", "local_task", "public", "local", "delta"])
        for r in table:
            writer.writerow(
                [
                    r["public_column"],
                    r["local_task"],
                    "" if r["public"] is None else f"{r['public']:.6f}",
                    "" if r["local"] is None else f"{r['local']:.6f}",
                    "" if r["delta"] is None else f"{r['delta']:.6f}",
                ]
            )
        writer.writerow([])
        writer.writerow(["aggregate", "value"])
        agg_labels = [
            ("local_group_acc_weighted", "local group acc (sample-weighted)"),
            ("local_unweighted_mean", "local unweighted task mean"),
            ("public_average_reported", "public average (reported)"),
            ("public_unweighted_mean_computed", "public unweighted mean (computed)"),
            ("delta_unweighted", "delta unweighted (local mean - public mean)"),
        ]
        for key, label in agg_labels:
            value = aggregates[key]
            writer.writerow([label, "" if value is None else f"{value:.6f}"])


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare a local lm-eval result against the public GSMA Open Telco "
            "leaderboard, task-wise."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--local-result",
        required=True,
        type=Path,
        help="Path to the local lm-eval result JSON.",
    )
    parser.add_argument(
        "--model",
        default="gemma3-4b",
        help="Public leaderboard model row to load (default: gemma3-4b).",
    )
    parser.add_argument(
        "--public-json",
        type=Path,
        default=None,
        help=(
            "Optional manual public-row JSON fallback (column->score or "
            "column->[score, stderr]). Bypasses the datasets download."
        ),
    )
    parser.add_argument(
        "--map",
        dest="map_overrides",
        action="append",
        default=[],
        metavar="public_col=local_task",
        help=(
            "Override a public-column -> local-task mapping. Repeatable. "
            "Applied on top of the auto-detected default mapping."
        ),
    )
    parser.add_argument(
        "--track",
        choices=["auto", "ot-lite", "ot-full"],
        default="auto",
        help="Force the track instead of auto-detecting from task names.",
    )
    parser.add_argument(
        "--profile",
        choices=["default", "gsma"],
        default="default",
        help=(
            "Mapping/output profile. 'default' (the default) maps public columns "
            "to the frozen multiple_choice/generate tasks and is byte-identical to "
            "prior behavior. 'gsma' maps to the non-default *_mcgen / *_gsma tasks, "
            "emits the per-task delta table first, labels the single mean as a "
            "leaderboard convention, and annotates the unaligned MC rows."
        ),
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=None,
        help="Optional path to write the comparison as Markdown.",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=None,
        help="Optional path to write the comparison as CSV.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        local = load_local_result(args.local_result)

        track = detect_track(local) if args.track == "auto" else args.track
        mapping = dict(get_mapping(track, args.profile))
        mapping.update(parse_mapping_overrides(args.map_overrides))
        group_name = get_group_name(track, args.profile)

        local_scores = extract_local_scores(local, mapping)
        local_group_acc = extract_local_group_acc(local, group_name)

        if args.public_json is not None:
            public_scores, public_average = load_public_from_json(
                args.public_json, mapping
            )
            public_source = f"manual JSON ({args.public_json})"
        else:
            public_scores, public_average = load_public_from_dataset(
                args.model, mapping
            )
            public_source = "GSMA/leaderboard (datasets)"

        table = build_table(mapping, public_scores, local_scores)
        aggregates = compute_aggregates(table, public_average, local_group_acc)

        if args.profile == "gsma":
            stdout_text = render_stdout_gsma(
                track, args.model, public_source, table, aggregates
            )
        else:
            stdout_text = render_stdout(
                track, args.model, public_source, table, aggregates
            )
        print(stdout_text)

        if args.out_md is not None:
            if args.profile == "gsma":
                md_text = render_markdown_gsma(
                    track, args.model, public_source, table, aggregates
                )
            else:
                md_text = render_markdown(
                    track, args.model, public_source, table, aggregates
                )
            args.out_md.parent.mkdir(parents=True, exist_ok=True)
            args.out_md.write_text(md_text, encoding="utf-8")
            _eprint(f"Wrote Markdown: {args.out_md}")

        if args.out_csv is not None:
            args.out_csv.parent.mkdir(parents=True, exist_ok=True)
            write_csv(args.out_csv, table, aggregates)
            _eprint(f"Wrote CSV: {args.out_csv}")

        return 0
    except CompareError as exc:
        _eprint(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
