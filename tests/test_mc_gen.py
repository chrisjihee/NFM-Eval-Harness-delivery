"""Tests for the NON-DEFAULT generation-based multiple-choice helpers.

These cover the additive ``doc_to_text_mc_gen`` / ``extract_mc_letter`` /
``process_results_mc_gen`` helpers in
``open_telco_lm_eval/tasks/open_telco_otlite/utils.py``. utils is loaded by
file path (the tasks directory is not an importable package).
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
# Leak-guard: prompt must be independent of the gold label and must not leak it.
# Uses the real dataset; skips cleanly when the dataset cannot be loaded
# (e.g. no network).
# ---------------------------------------------------------------------------


def _load_teleqna_head(n: int):
    try:
        import datasets
    except ImportError:  # pragma: no cover - environment dependent
        pytest.skip("datasets not installed")

    try:
        ds = datasets.load_dataset("GSMA/ot-lite", "teleqna", split="test")
    except Exception as exc:  # pragma: no cover - network dependent
        pytest.skip(f"GSMA/ot-lite teleqna unavailable: {exc}")

    return [ds[i] for i in range(min(n, len(ds)))]


def test_mc_gen_prompt_is_independent_of_gold():
    docs = _load_teleqna_head(20)
    assert docs, "expected at least one doc"

    for doc in docs:
        choices = list(doc["choices"])
        baseline = utils.doc_to_text_mc_gen(doc)

        # Mutating the gold label must not change the rendered prompt.
        for alt_answer in range(len(choices)):
            mutated = dict(doc)
            mutated["answer"] = alt_answer
            assert utils.doc_to_text_mc_gen(mutated) == baseline


def test_mc_gen_prompt_does_not_expose_gold_letter():
    docs = _load_teleqna_head(20)
    assert docs, "expected at least one doc"

    for doc in docs:
        prompt = utils.doc_to_text_mc_gen(doc)
        gold_idx = int(doc["answer"])
        gold_letter = utils.CHOICE_LABELS[gold_idx]
        # The prompt must not directly reveal the answer, e.g. "Answer: C".
        assert f"Answer: {gold_letter}" not in prompt
        assert f"answer is {gold_letter}" not in prompt.lower()


# ---------------------------------------------------------------------------
# extract_mc_letter unit tests (synthetic).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,num_choices,expected",
    [
        ("A", 4, 0),
        ("The answer is C.", 4, 2),
        ("\\boxed{B}", 4, 1),
        ("answer: d", 4, 3),
        ("정답 없음", 4, None),  # no in-range letter
        ("Z", 4, None),  # out of range
        ("E", 4, None),  # out of range for 4 choices
        ("E", 5, 4),  # in range when 5 choices
        ("Final answer: A", 5, 0),
        ("The best option is B because ...", 4, 1),
        ("", 4, None),
        (None, 4, None),
        ("C", 0, None),  # invalid num_choices
    ],
)
def test_extract_mc_letter(text, num_choices, expected):
    assert utils.extract_mc_letter(text, num_choices) == expected


def test_extract_mc_letter_boxed_takes_priority():
    # boxed letter wins over a later "answer is" cue and stray letters.
    assert utils.extract_mc_letter("\\boxed{D} the answer is A", 4) == 3


# ---------------------------------------------------------------------------
# process_results_mc_gen unit tests (synthetic doc).
# ---------------------------------------------------------------------------


def _doc(answer: int, num_choices: int = 4):
    return {
        "question": "What is the capital metric?",
        "choices": [f"choice {i}" for i in range(num_choices)],
        "answer": answer,
    }


def test_process_results_correct():
    assert utils.process_results_mc_gen(_doc(2), ["C"]) == {"acc": 1.0}


def test_process_results_incorrect():
    assert utils.process_results_mc_gen(_doc(2), ["A"]) == {"acc": 0.0}


def test_process_results_unparsable_is_zero():
    assert utils.process_results_mc_gen(_doc(2), ["no letter here"]) == {"acc": 0.0}


def test_process_results_empty_results_is_zero():
    assert utils.process_results_mc_gen(_doc(2), []) == {"acc": 0.0}


def test_process_results_gold_is_choices_index():
    # gold is an int index into choices; pred letter must map to that index.
    assert utils.process_results_mc_gen(_doc(0), ["A"]) == {"acc": 1.0}
    assert utils.process_results_mc_gen(_doc(3), ["D"]) == {"acc": 1.0}
