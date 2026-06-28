"""Helpers for Open Telco custom lm-eval tasks."""

from __future__ import annotations

import json
import math
import os
import re
import string
from fractions import Fraction
from pathlib import Path
from typing import Any


CHOICE_LABELS = tuple(string.ascii_uppercase)
THREE_GPP_LABELS = (
    "CT1",
    "CT3",
    "CT4",
    "CT6",
    "RAN1",
    "RAN2",
    "RAN3",
    "RAN4",
    "RAN5",
    "RAN_AH1",
    "SA1",
    "SA2",
    "SA3",
    "SA4",
    "SA5",
    "SA6",
)
THREE_GPP_LABEL_SET = frozenset(THREE_GPP_LABELS)
ROOT_CAUSE_LABELS = tuple(f"C{i}" for i in range(1, 9))
ROOT_CAUSE_LABEL_SET = frozenset(ROOT_CAUSE_LABELS)
ROOT_DIR = Path(__file__).resolve().parents[3]
BOXED_RE = re.compile(r"\\boxed\{([^{}]+)\}")
NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|[-+]?\d+\s*/\s*[-+]?\d+")
WORKING_GROUP_RE = re.compile(
    r'["\']?WORKING\s*GROUP["\']?\s*:\s*["\']?([A-Za-z0-9_]+)["\']?',
    flags=re.IGNORECASE,
)
FINAL_ANSWER_RE = re.compile(
    r"(?:final answer|answer)\s*(?:is|:)\s*([^\n\r.;]+)",
    flags=re.IGNORECASE,
)
ROOT_CAUSE_RE = re.compile(r"\bC([1-8])\b", flags=re.IGNORECASE)


def _format_choices(choices: list[str]) -> str:
    lines = []
    for idx, choice in enumerate(choices):
        label = CHOICE_LABELS[idx]
        lines.append(f"{label}. {choice}")
    return "\n".join(lines)


def doc_to_text_mc(doc: dict[str, Any]) -> str:
    question = doc["question"].strip()
    choices = doc["choices"]
    return (
        "You are answering a telecommunications domain benchmark question.\n"
        "Select the single best answer.\n\n"
        f"Question: {question}\n"
        "Choices:\n"
        f"{_format_choices(choices)}\n\n"
        "Answer:"
    )


def doc_to_text_3gpp_tsg(doc: dict[str, Any]) -> str:
    question = doc["question"].strip()
    return (
        "You are answering a 3GPP working-group classification question.\n"
        "Return only the most likely working group label.\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )


def _extract_3gpp_excerpt(question: str) -> str:
    match = re.search(r"###TEXT:\s*\{(.*)\}\s*$", question.strip(), flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return question.strip()


def doc_to_text_3gpp_mc(doc: dict[str, Any]) -> str:
    excerpt = _extract_3gpp_excerpt(doc["question"])
    return (
        "You are classifying a 3GPP document excerpt by working group.\n"
        "Select the single best answer from the choices.\n\n"
        f"Document excerpt:\n{excerpt}\n\n"
        "Choices:\n"
        f"{_format_choices(list(THREE_GPP_LABELS))}\n\n"
        "Answer:"
    )


def doc_to_choice_3gpp_tsg(doc: dict[str, Any]) -> list[str]:
    del doc
    return list(THREE_GPP_LABELS)


def doc_to_target_3gpp_tsg(doc: dict[str, Any]) -> int:
    return THREE_GPP_LABELS.index(doc["answer"])


def doc_to_target_text(doc: dict[str, Any]) -> str:
    return str(doc["answer"]).strip()


def doc_to_text_3gpp_generate(doc: dict[str, Any]) -> str:
    excerpt = _extract_3gpp_excerpt(doc["question"])
    labels = ", ".join(THREE_GPP_LABELS)
    return (
        "You are classifying a 3GPP technical-document excerpt by working group.\n"
        f"Choose exactly one label from: {labels}.\n"
        'Return only JSON in this format: {"WORKING GROUP": "LABEL"}.\n\n'
        f"Document excerpt:\n{excerpt}\n\n"
        "Answer:"
    )


def _normalize_token(text: str) -> str:
    return text.strip().upper().replace("-", "_").replace(" ", "_")


def extract_3gpp_label(text: str) -> str | None:
    if not isinstance(text, str):
        return None

    text = text.strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            value = parsed.get("WORKING GROUP") or parsed.get("working group")
            if isinstance(value, str):
                normalized = _normalize_token(value)
                if normalized in THREE_GPP_LABEL_SET:
                    return normalized
    except json.JSONDecodeError:
        pass

    match = WORKING_GROUP_RE.search(text)
    if match:
        normalized = _normalize_token(match.group(1))
        if normalized in THREE_GPP_LABEL_SET:
            return normalized

    for label in sorted(THREE_GPP_LABELS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(label)}\b", text, flags=re.IGNORECASE):
            return label

    return None


def process_results_3gpp_generate(
    doc: dict[str, Any], results: list[str]
) -> dict[str, int]:
    prediction = extract_3gpp_label(results[0] if results else "")
    gold = _normalize_token(str(doc["answer"]))
    return {"acc": int(prediction == gold)}


def doc_to_text_telemath(doc: dict[str, Any]) -> str:
    question = doc["question"].strip()
    return (
        "You are solving a telecommunications math problem.\n"
        "Return only the final numeric answer.\n"
        "If needed, you may use scientific notation.\n\n"
        f"Problem: {question}\n"
        "Answer:"
    )


def _clean_numeric_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = cleaned.replace(",", "")
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace("\\(", "").replace("\\)", "")
    cleaned = cleaned.replace("{", "").replace("}", "")
    return cleaned.strip()


def _coerce_number(text: str) -> float | None:
    candidate = _clean_numeric_text(text)
    if not candidate:
        return None

    if re.fullmatch(r"[-+]?\d+\s*/\s*[-+]?\d+", candidate):
        try:
            return float(Fraction(candidate.replace(" ", "")))
        except (ValueError, ZeroDivisionError):
            return None

    try:
        return float(candidate)
    except ValueError:
        return None


def extract_telemath_answer(text: str) -> float | None:
    if not isinstance(text, str):
        return None

    boxed = BOXED_RE.findall(text)
    if boxed:
        number = _coerce_number(boxed[-1])
        if number is not None:
            return number

    final_answer = FINAL_ANSWER_RE.search(text)
    if final_answer:
        number = _coerce_number(final_answer.group(1))
        if number is not None:
            return number

    numbers = NUMBER_RE.findall(text)
    for candidate in reversed(numbers):
        number = _coerce_number(candidate)
        if number is not None:
            return number

    return None


def process_results_telemath(
    doc: dict[str, Any], results: list[str]
) -> dict[str, int]:
    prediction = extract_telemath_answer(results[0] if results else "")
    gold = _coerce_number(str(doc["answer"]))
    if prediction is None or gold is None:
        return {"acc": 0}

    return {"acc": int(math.isclose(prediction, gold, rel_tol=1e-6, abs_tol=1e-8))}


def doc_to_text_telelogs(doc: dict[str, Any]) -> str:
    question = doc["question"].strip()
    return (
        f"{question}\n\n"
        "Return only the final root-cause label such as C1, C2, ..., or C8.\n"
        "Answer:"
    )


def extract_telelogs_label(text: str) -> str | None:
    if not isinstance(text, str):
        return None

    boxed = BOXED_RE.findall(text)
    for candidate in reversed(boxed):
        candidate = candidate.strip().upper()
        if candidate in ROOT_CAUSE_LABEL_SET:
            return candidate
        if re.fullmatch(r"[1-8]", candidate):
            return f"C{candidate}"

    matches = ROOT_CAUSE_RE.findall(text)
    if matches:
        return f"C{matches[-1]}"

    numbers = re.findall(r"\b([1-8])\b", text)
    if numbers:
        return f"C{numbers[-1]}"

    return None


def process_results_telelogs(
    doc: dict[str, Any], results: list[str]
) -> dict[str, int]:
    prediction = extract_telelogs_label(results[0] if results else "")
    gold = str(doc["answer"]).strip().upper()
    return {"acc": int(prediction == gold)}


def _teletables_roots() -> list[Path]:
    env_root = os.environ.get("TELETABLES_ROOT")
    roots = [
        Path(env_root) if env_root else None,
        ROOT_DIR / "tables",
        ROOT_DIR / "data" / "TeleTables" / "tables",
        ROOT_DIR / ".cache_hf" / "TeleTables" / "tables",
    ]
    return [root for root in roots if root is not None]


def _load_teletable_context(doc: dict[str, Any]) -> str | None:
    document_id = str(doc["document_id"]).strip()
    table_id = str(doc["table_id"]).strip()
    candidate_suffixes = ("table.md", "table.html", "table.json")

    for root in _teletables_roots():
        for suffix in candidate_suffixes:
            table_path = root / document_id / table_id / suffix
            if table_path.is_file():
                try:
                    content = table_path.read_text(encoding="utf-8").strip()
                except UnicodeDecodeError:
                    content = table_path.read_text(encoding="latin-1").strip()
                if content:
                    if len(content) > 12000:
                        content = content[:12000].rstrip() + "\n...[truncated]"
                    return f"{suffix}:\n{content}"
    return None


def doc_to_text_teletables(doc: dict[str, Any]) -> str:
    metadata = (
        f"Table title: {doc['table_title'].strip()}\n"
        f"Document title: {doc['document_title'].strip()}"
    )
    table_context = _load_teletable_context(doc)
    if table_context:
        context_block = f"Table content:\n{table_context}"
    else:
        context_block = (
            "Table content: [not available in the public GSMA/ot-full row; "
            "set TELETABLES_ROOT to the extracted TeleTables tables directory to "
            "inject the original table content automatically]"
        )

    return (
        "You are answering a telecommunications table-understanding question.\n"
        "Use the table metadata and any available table content to select the "
        "single best answer.\n\n"
        f"{metadata}\n"
        f"{context_block}\n\n"
        f"Question: {doc['question'].strip()}\n"
        "Choices:\n"
        f"{_format_choices(doc['choices'])}\n\n"
        "Answer:"
    )


# ---------------------------------------------------------------------------
# NON-DEFAULT experimental: generation-based multiple-choice scoring.
#
# These helpers power an *additive* generate_until variant of the standard
# multiple_choice tasks. They never change the behaviour of the default
# multiple_choice scoring path (doc_to_text_mc / doc_to_choice / acc / acc_norm).
#
# Integrity note: the rendered prompt depends only on doc["question"] and
# doc["choices"]; it never reads doc["answer"] / gold. The same doc always
# renders the same prompt regardless of the gold label (no answer leakage).
# ---------------------------------------------------------------------------

_MC_GEN_ANSWER_CUE_RE = re.compile(
    r"(?:final answer|answer)\s*(?:is|:)\s*\**\s*([A-Za-z])\b",
    flags=re.IGNORECASE,
)
_MC_GEN_FIRST_LETTER_RE = re.compile(r"\b([A-Za-z])\b")


def doc_to_text_mc_gen(doc: dict[str, Any]) -> str:
    """Render a generation-style multiple-choice prompt.

    Builds the same question + choices context as ``doc_to_text_mc`` but ends
    with a single-letter response instruction. Uses only ``doc["question"]``
    and ``doc["choices"]`` -- never ``doc["answer"]`` -- so the prompt is
    independent of the gold label (no answer leakage).
    """
    question = doc["question"].strip()
    choices = doc["choices"]
    return (
        "You are answering a telecommunications domain benchmark question.\n"
        "Select the single best answer.\n\n"
        f"Question: {question}\n"
        "Choices:\n"
        f"{_format_choices(choices)}\n\n"
        "Respond with ONLY the letter of the correct choice "
        "(for example: A). Do not explain.\n"
        "Answer:"
    )


def extract_mc_letter(text: str, num_choices: int) -> int | None:
    """Extract a choice letter (A..) from generated text -> 0-based index.

    Resolution order:
      1. ``\\boxed{X}`` -- last boxed single letter in range.
      2. A letter following an "answer is" / "answer:" / "final answer" cue.
      3. The first standalone letter (word boundary, case-insensitive) in range.

    Returns the 0-based choice index, or ``None`` if no in-range letter is
    found. ``num_choices`` bounds the valid letters to A..(A+num_choices-1).
    """
    if not isinstance(text, str):
        return None
    if not isinstance(num_choices, int) or num_choices <= 0:
        return None

    max_choices = min(num_choices, len(CHOICE_LABELS))

    def _to_index(letter: str) -> int | None:
        idx = ord(letter.upper()) - ord("A")
        if 0 <= idx < max_choices:
            return idx
        return None

    for candidate in reversed(BOXED_RE.findall(text)):
        candidate = candidate.strip()
        if len(candidate) == 1 and candidate.isalpha():
            idx = _to_index(candidate)
            if idx is not None:
                return idx

    cue = _MC_GEN_ANSWER_CUE_RE.search(text)
    if cue:
        idx = _to_index(cue.group(1))
        if idx is not None:
            return idx

    for match in _MC_GEN_FIRST_LETTER_RE.finditer(text):
        idx = _to_index(match.group(1))
        if idx is not None:
            return idx

    return None


def process_results_mc_gen(
    doc: dict[str, Any], results: list[str]
) -> dict[str, float]:
    """Score a generation-based multiple-choice prediction.

    Extracts a predicted 0-based index from ``results[0]`` via
    ``extract_mc_letter`` and compares it to ``int(doc["answer"])`` (the same
    0-based choices index used by the default multiple_choice scoring).
    """
    text = results[0] if results else ""
    prediction = extract_mc_letter(text, len(doc["choices"]))
    gold = int(doc["answer"])
    if prediction is None:
        return {"acc": 0.0}
    return {"acc": 1.0 if prediction == gold else 0.0}


# ---------------------------------------------------------------------------
# GSMA-aligned generation scoring (scorer rules mirror gsma-evals source).
# Additive; default multiple_choice/generate paths unchanged. Prompts read only
# doc[question]/doc[choices]; gold (doc[answer]) used ONLY as scoring target,
# never injected. New functions AND new module constants are re-exported to
# ot-full via importlib (affects both tracks).
# ---------------------------------------------------------------------------

from textwrap import dedent as _dedent

# parse_boxed_answer (telemath/telelogs) mirror: capture last \boxed{...} content,
# allowing one level of nested braces. Matches gsma-evals BOXED_PATTERN.
BOXED_NESTED_RE = re.compile(r"\\boxed\{((?:[^{}]|\{[^{}]*\})*)\}")
# three_gpp WG_PATTERN mirror: working-group token capture.
WG_GSMA_RE = re.compile(r"([A-Z]+\d+(?:-[A-Z]+)?)")
# gsma-evals WHITESPACE_PATTERN mirror: collapse newline + following whitespace.
WS_COLLAPSE_RE = re.compile(r"\n\s*")
# telelogs DIGIT_PATTERN mirror: first run of digits.
DIGIT_GSMA_RE = re.compile(r"\d+")

# Verbatim copy of gsma-evals telemath SYSTEM_PROMPT (telemath.py); built with
# dedent(...).strip() exactly as upstream so the resulting text is byte-identical.
TELEMATH_SYSTEM_PROMPT_GSMA = _dedent(r"""
    You are an expert problem solver. Your task is to solve numerical exercises by following these guidelines:
    1.  **Understand the Goal:** Clearly identify what the problem is asking you to find, paying close attention to the required units for the final answer.
    2.  **Reason Step-by-Step:** Provide a clear, sequential reasoning process. Explain the formulas, principles, or logic used in each step. Show intermediate calculations if they clarify your thought process. The detailed structure of your sub-steps is up to you, as long as the reasoning is sound and easy to follow.
    3.  **Unit Management:**
        *   Track units throughout your calculations.
        *   **Crucially, ensure your final numerical answer is converted to the specific units requested in the problem statement.** If intermediate calculations result in a different unit, perform a final conversion step.
        *   State the unit of the final answer clearly in your explanatory text *before* the boxed answer.
    4.  **Final Numerical Answer Format:**
        *   The final answer must be a single numerical value (integer or float).
        *   Present this numerical value exclusively within the `\$\boxed{{...}}\$` format.
        *   **CRITICAL:** The `\$\boxed{{...}}\$` block must contain *only* the number. No text, no units, no labels (e.g., NOT `\$\boxed{{Result: 50}}\$` or `\$\boxed{{50 \text{{ mA}}}}\$`, but `\$\boxed{{50}}\$`).
    """).strip()


def extract_boxed_last(text: str) -> str:
    r"""Return last ``\boxed{...}`` content, normalized like gsma parse_boxed_answer.

    Mirrors gsma-evals ``parse_boxed_answer``: empty/None -> ""; take the last
    match of :data:`BOXED_NESTED_RE`, ``.strip()`` it, collapse newline-leading
    whitespace via :data:`WS_COLLAPSE_RE`, then ``lstrip(":")`` and ``rstrip("./")``.
    """
    if not text:
        return ""
    matches = BOXED_NESTED_RE.findall(text)
    if not matches:
        return ""
    answer = WS_COLLAPSE_RE.sub("", matches[-1].strip())
    return answer.lstrip(":").rstrip("./")


def doc_to_text_telemath_gsma(doc: dict[str, Any]) -> str:
    """telemath prompt: gsma SYSTEM_PROMPT header + blank line + raw question.

    lm-eval has no system-solver stage, so the upstream ``system_message`` is
    merged into a single prompt. Reads only ``doc["question"]``; gold untouched.
    """
    return f"{TELEMATH_SYSTEM_PROMPT_GSMA}\n\n{doc['question']}"


def process_results_telemath_gsma(
    doc: dict[str, Any], results: list[str]
) -> dict[str, float]:
    """Score telemath generation per gsma telemath_scorer.

    pred = last boxed content; target = str(answer). Correct if
    ``math.isclose(float(pred), float(target), rel_tol=0.01, abs_tol=0.01)``;
    on ValueError/TypeError fall back to exact string equality.
    """
    pred = extract_boxed_last(results[0] if results else "")
    target = str(doc["answer"]).strip()
    try:
        ok = math.isclose(float(pred), float(target), rel_tol=0.01, abs_tol=0.01)
    except (ValueError, TypeError):
        ok = pred == target
    return {"acc": 1.0 if ok else 0.0}


def doc_to_text_telelogs_gsma(doc: dict[str, Any]) -> str:
    """telelogs prompt: raw question only, no instructions (gsma uses bare generate())."""
    return str(doc["question"]).strip()


def extract_first_int(text: str) -> int | None:
    """First run of digits in ``text`` as int, else None (gsma extract_first_int)."""
    match = DIGIT_GSMA_RE.search(text)
    if match:
        return int(match.group())
    return None


def process_results_telelogs_gsma(
    doc: dict[str, Any], results: list[str]
) -> dict[str, float]:
    """Score telelogs generation per gsma soft scorer.

    pred = first int of last boxed content; gt = first int of str(answer);
    correct iff both present and equal.
    """
    pred = extract_first_int(extract_boxed_last(results[0] if results else ""))
    gt = extract_first_int(str(doc["answer"]))
    return {"acc": 1.0 if (pred is not None and pred == gt) else 0.0}


def doc_to_text_3gpp_gsma(doc: dict[str, Any]) -> str:
    """3gpp prompt: raw question only, no JSON/template (gsma uses bare generate())."""
    return str(doc["question"]).strip()


def extract_wg_token(text: str, last: bool = False) -> str | None:
    """Working-group token via gsma WG_PATTERN, case-insensitive.

    Uses ``findall`` (group capture) over :data:`WG_GSMA_RE`. Default ``last=False``
    returns the first match (gsma ``pattern`` scorer uses the first match);
    ``last=True`` returns the last match. None if no match.
    """
    matches = re.findall(WG_GSMA_RE.pattern, text, flags=re.IGNORECASE)
    if not matches:
        return None
    return matches[-1] if last else matches[0]


def process_results_3gpp_gsma(
    doc: dict[str, Any], results: list[str]
) -> dict[str, float]:
    """Score 3gpp generation per gsma pattern scorer (case-insensitive, first match)."""
    pred = extract_wg_token(results[0] if results else "")
    ans = str(doc["answer"]).strip()
    return {"acc": 1.0 if (pred is not None and pred.lower() == ans.lower()) else 0.0}


def doc_to_text_telelogs_gsma_hinted(doc: dict[str, Any]) -> str:
    """telelogs raw question + one output-format line (collapse-gate fallback; gold-free)."""
    question = str(doc["question"]).strip()
    return f"{question}\n\nPut your final root-cause label in \\boxed{{}}."


def doc_to_text_3gpp_gsma_hinted(doc: dict[str, Any]) -> str:
    """3gpp raw question + one output-format line (collapse-gate fallback; gold-free)."""
    question = str(doc["question"]).strip()
    return f"{question}\n\nEnd with the working group label, e.g. SA5."
