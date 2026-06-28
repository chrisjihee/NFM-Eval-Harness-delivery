"""Characterization tests for existing generation parsers.

These lock in the CURRENT behavior of ``extract_telemath_answer``,
``extract_telelogs_label``, and ``extract_3gpp_label``. They are a regression
guard, NOT a behavior change: if any of these assertions start failing, the
default scoring behavior has shifted and must be reviewed.

utils is loaded by file path (the tasks directory is not an importable
package).
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest


_UTILS_PATH = (
    Path(__file__).resolve().parents[1]
    / "open_telco_lm_eval"
    / "tasks"
    / "open_telco_otlite"
    / "utils.py"
)


def _load_utils():
    spec = importlib.util.spec_from_file_location("open_telco_otlite_utils", _UTILS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load_utils()


# ---------------------------------------------------------------------------
# extract_telemath_answer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The answer is 42", 42.0),
        ("\\boxed{3.14}", 3.14),
        ("answer is 7", 7.0),
        ("approximately 100 units", 100.0),
        ("no number here", None),
    ],
)
def test_extract_telemath_answer_characterization(text, expected):
    result = utils.extract_telemath_answer(text)
    if expected is None:
        assert result is None
    else:
        assert result is not None
        assert math.isclose(result, expected, rel_tol=1e-9, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# extract_telelogs_label
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The root cause is C3.", "C3"),
        ("\\boxed{5}", "C5"),
        ("\\boxed{C2}", "C2"),
        ("It is 7", "C7"),
        ("C1 then C8", "C8"),  # last match wins
        ("C9", None),  # out of C1..C8 range
        ("nothing", None),
    ],
)
def test_extract_telelogs_label_characterization(text, expected):
    assert utils.extract_telelogs_label(text) == expected


# ---------------------------------------------------------------------------
# extract_3gpp_label
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ('{"WORKING GROUP": "RAN2"}', "RAN2"),
        ("WORKING GROUP: SA5", "SA5"),
        ("working group: ran_ah1", "RAN_AH1"),
        ("I think this belongs to CT1.", "CT1"),
        ("no label", None),
    ],
)
def test_extract_3gpp_label_characterization(text, expected):
    assert utils.extract_3gpp_label(text) == expected
