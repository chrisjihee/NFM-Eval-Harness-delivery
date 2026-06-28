"""Helpers for Open Telco ot-full custom lm-eval tasks."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_OTLITE_UTILS_PATH = Path(__file__).resolve().parents[1] / "open_telco_otlite" / "utils.py"
_SPEC = importlib.util.spec_from_file_location("open_telco_otlite_utils", _OTLITE_UTILS_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load ot-lite utils from {_OTLITE_UTILS_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

# Wildcard re-exports ALL non-underscore symbols (funcs + constants) from ot-lite utils; new *_gsma symbols are added in ot-lite only and surface here automatically.
for _name in dir(_MODULE):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_MODULE, _name)
