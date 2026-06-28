"""Tests for the NON-DEFAULT GSMA-aligned generation scoring helpers.

These cover the additive ``extract_boxed_last`` / ``extract_first_int`` /
``extract_wg_token`` parsers and the ``process_results_*_gsma`` scorers in
``open_telco_lm_eval/tasks/open_telco_otlite/utils.py``, plus a leak-guard for
the ``teletables`` generation-based MC variant (``doc_to_text_mc_gen``).

These scorers mirror the gsma-evals source contract (telemath isclose
rel/abs_tol=0.01 + exact-string fallback; telelogs soft = first int of last
boxed; 3gpp WG pattern first-match case-insensitive). They are additive and do
not change any default scoring path.

utils is loaded by file path (the tasks directory is not an importable
package); synthetic docs are used so no network/dataset access is required.
"""

from __future__ import annotations

import importlib.util
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
# extract_boxed_last (gsma parse_boxed_answer mirror).
# ---------------------------------------------------------------------------


def test_extract_boxed_last_nested_brace():
    # A single boxed value containing one level of nested braces.
    assert utils.extract_boxed_last(r"\boxed{50 \text{ mA}}") == r"50 \text{ mA}"


def test_extract_boxed_last_multiple_takes_last():
    assert utils.extract_boxed_last(r"\boxed{1} then \boxed{2} and \boxed{3}") == "3"


def test_extract_boxed_last_trims_leading_colon_and_trailing_dot_slash():
    # lstrip(":") + rstrip("./") normalization.
    assert utils.extract_boxed_last(r"\boxed{:42./}") == "42"
    assert utils.extract_boxed_last(r"\boxed{::C6.}") == "C6"


def test_extract_boxed_last_collapses_internal_newline_whitespace():
    # WS_COLLAPSE_RE removes a newline and its trailing whitespace.
    assert utils.extract_boxed_last("\\boxed{12\n  34}") == "1234"


@pytest.mark.parametrize("text", ["", None, "no box here", r"\boxed"])
def test_extract_boxed_last_empty_and_missing(text):
    assert utils.extract_boxed_last(text) == ""


# ---------------------------------------------------------------------------
# telemath: process_results_telemath_gsma.
# ---------------------------------------------------------------------------


def _telemath_doc(answer):
    return {"question": "Compute the current in mA.", "answer": answer}


def test_telemath_within_1pct_tolerance_boundary_pass():
    # 99.5 vs 100 -> 0.5% off, within rel_tol=0.01 -> correct.
    doc = _telemath_doc(100)
    assert utils.process_results_telemath_gsma(doc, [r"\boxed{99.5}"]) == {"acc": 1.0}


def test_telemath_outside_tolerance_fail():
    # 90 vs 100 -> 10% off -> incorrect.
    doc = _telemath_doc(100)
    assert utils.process_results_telemath_gsma(doc, [r"\boxed{90}"]) == {"acc": 0.0}


def test_telemath_non_numeric_target_exact_string_fallback():
    # target is non-numeric -> float() raises -> exact-string equality fallback.
    doc = _telemath_doc("on")
    assert utils.process_results_telemath_gsma(doc, [r"\boxed{on}"]) == {"acc": 1.0}
    assert utils.process_results_telemath_gsma(doc, [r"\boxed{off}"]) == {"acc": 0.0}


def test_telemath_no_boxed_output_collapses_to_fail():
    # No boxed -> pred == "" -> float("") raises -> exact compare "" != "100" -> fail.
    doc = _telemath_doc(100)
    assert utils.process_results_telemath_gsma(doc, ["no box"]) == {"acc": 0.0}


def test_telemath_empty_results_is_fail():
    doc = _telemath_doc(100)
    assert utils.process_results_telemath_gsma(doc, []) == {"acc": 0.0}


# ---------------------------------------------------------------------------
# telelogs: extract_first_int + process_results_telelogs_gsma (soft scorer).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("C6", 6),
        ("the answer is 42 widgets", 42),
        ("no digits", None),
        ("", None),
    ],
)
def test_extract_first_int(text, expected):
    assert utils.extract_first_int(text) == expected


def _telelogs_doc(answer):
    return {"question": "Diagnose the root cause from the log.", "answer": answer}


def test_telelogs_boxed_label_matches():
    # \boxed{C6} -> first int 6; target "C6" -> first int 6 -> correct.
    doc = _telelogs_doc("C6")
    assert utils.process_results_telelogs_gsma(doc, [r"\boxed{C6}"]) == {"acc": 1.0}


def test_telelogs_no_boxed_collapses_to_fail():
    # No boxed -> extract_boxed_last "" -> extract_first_int None -> incorrect.
    doc = _telelogs_doc("C6")
    assert utils.process_results_telelogs_gsma(doc, ["root cause is C6"]) == {"acc": 0.0}


def test_telelogs_soft_other_text_same_first_int_is_correct():
    # Soft semantics: pred text differs but first int of boxed matches gold's.
    doc = _telelogs_doc("C6")
    assert utils.process_results_telelogs_gsma(doc, [r"\boxed{6 retries}"]) == {"acc": 1.0}


def test_telelogs_wrong_int_is_fail():
    doc = _telelogs_doc("C6")
    assert utils.process_results_telelogs_gsma(doc, [r"\boxed{C3}"]) == {"acc": 0.0}


# ---------------------------------------------------------------------------
# 3gpp: extract_wg_token + process_results_3gpp_gsma (WG pattern, first-match).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("SA5", "SA5"),
        ("RAN1", "RAN1"),
        ("RAN_AH1", "AH1"),  # WG_GSMA_RE matches [A-Z]+\d+ -> the AH1 token
        ("CT4", "CT4"),
        ("the group is sa5 here", "sa5"),  # case-insensitive capture
    ],
)
def test_extract_wg_token_first_match(text, expected):
    assert utils.extract_wg_token(text) == expected


def test_extract_wg_token_first_vs_last():
    text = "first SA2 then later RAN3"
    assert utils.extract_wg_token(text) == "SA2"  # default first
    assert utils.extract_wg_token(text, last=False) == "SA2"
    assert utils.extract_wg_token(text, last=True) == "RAN3"


def test_extract_wg_token_no_match_is_none():
    assert utils.extract_wg_token("no working group token") is None
    assert utils.extract_wg_token("") is None


def _3gpp_doc(answer):
    return {"question": "Classify this 3GPP excerpt.", "answer": answer}


def test_3gpp_first_match_correct():
    doc = _3gpp_doc("SA5")
    assert utils.process_results_3gpp_gsma(doc, ["The working group is SA5."]) == {"acc": 1.0}


def test_3gpp_raw_answer_case_insensitive_equality():
    # pred "sa5" vs raw answer "SA5" -> case-insensitive equal -> correct.
    doc = _3gpp_doc("SA5")
    assert utils.process_results_3gpp_gsma(doc, ["sa5"]) == {"acc": 1.0}
    # And the reverse: lower-case gold, upper-case pred.
    doc_lower = _3gpp_doc("ran1")
    assert utils.process_results_3gpp_gsma(doc_lower, ["RAN1"]) == {"acc": 1.0}


def test_3gpp_no_match_is_fail():
    doc = _3gpp_doc("SA5")
    assert utils.process_results_3gpp_gsma(doc, ["no group token here"]) == {"acc": 0.0}


def test_3gpp_wrong_token_is_fail():
    doc = _3gpp_doc("SA5")
    assert utils.process_results_3gpp_gsma(doc, ["RAN1"]) == {"acc": 0.0}


# ---------------------------------------------------------------------------
# teletables MC-gen leak-guard (uses doc_to_text_mc_gen; gold never injected).
# ---------------------------------------------------------------------------


def _teletables_doc():
    # Mirrors the real GSMA/ot-full teletables row shape: question + choices +
    # 0-based int answer. Here answer=2 -> gold letter 'C'.
    return {
        "question": "Which row reports the peak throughput?",
        "choices": [
            "Row alpha value",
            "Row beta value",
            "Row gamma peak value",
            "Row delta value",
        ],
        "answer": 2,
    }


def test_teletables_mcgen_answer_is_zero_based_int_mapping():
    # dataset-drift guard: answer is a 0-based int and maps to letter 'C'.
    doc = _teletables_doc()
    answer = doc["answer"]
    assert isinstance(answer, int)
    assert chr(65 + int(answer)) == "C"


def test_teletables_mcgen_prompt_does_not_leak_gold_letter_or_text():
    doc = _teletables_doc()
    prompt = utils.doc_to_text_mc_gen(doc)
    gold_idx = int(doc["answer"])
    gold_letter = utils.CHOICE_LABELS[gold_idx]
    gold_text = doc["choices"][gold_idx]

    # The prompt must not directly reveal the gold letter as the answer.
    assert f"Answer: {gold_letter}" not in prompt
    assert f"answer is {gold_letter}" not in prompt.lower()
    # The prompt is built from question + all choices, so the gold choice TEXT
    # legitimately appears as one option; what must NOT happen is the gold being
    # singled out. Verify the rendered prompt is identical when the gold index
    # is mutated (no dependence on doc["answer"]).
    for alt in range(len(doc["choices"])):
        mutated = dict(doc)
        mutated["answer"] = alt
        assert utils.doc_to_text_mc_gen(mutated) == prompt
    # Gold text appears only as an enumerated choice line, never as a stated answer.
    assert f"Answer: {gold_text}" not in prompt


def test_teletables_mcgen_prompt_does_not_inject_table_content():
    # The MC-gen prompt uses ONLY question + choices (no table injection),
    # matching GSMA parity for the teletables_mcgen variant.
    doc = _teletables_doc()
    # Add table-bearing fields that the metadata prompt (doc_to_text_teletables)
    # would otherwise consult; doc_to_text_mc_gen must ignore them.
    doc["table_title"] = "SECRET TABLE TITLE TOKEN"
    doc["document_title"] = "SECRET DOC TITLE TOKEN"
    doc["table_id"] = "tbl-leak"
    doc["document_id"] = "doc-leak"
    prompt = utils.doc_to_text_mc_gen(doc)

    assert "SECRET TABLE TITLE TOKEN" not in prompt
    assert "SECRET DOC TITLE TOKEN" not in prompt
    assert "Table content" not in prompt
    assert "Table title" not in prompt
    # Question and choices ARE present.
    assert doc["question"] in prompt
    for choice in doc["choices"]:
        assert choice in prompt
