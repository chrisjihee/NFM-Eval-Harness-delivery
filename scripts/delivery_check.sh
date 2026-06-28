#!/usr/bin/env bash
# delivery_check.sh — INL delivery readiness gate.
#
# grep-only (ripgrep is NOT assumed present). Does not use `set -e` so every
# check runs and failures aggregate into one exit code. GPU is NOT required.
#
# Usage: bash scripts/delivery_check.sh   (or: make delivery-check)
set -uo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"
fail=0
ok()   { echo "PASS: $1"; }
bad()  { echo "FAIL: $1"; fail=1; }

# 1. working tree clean (validates .gitignore actually covers smoke/conf dirs etc.)
if [ -z "$(git status --porcelain)" ]; then ok "git tree clean"; else
  bad "git tree clean"; git status --porcelain | sed 's/^/    /'; fi

# 2. run-script syntax
if bash -n run_open_telco_otlite.sh run_open_telco_otfull.sh; then ok "run-script syntax (bash -n)"; else bad "run-script syntax"; fi

# 3. task smoke (GPU-free task loading)
if bash scripts/smoke_test.sh >/dev/null 2>&1; then ok "task smoke (make smoke)"; else bad "task smoke"; fi

# 4. unit tests
if "$PY" -m pytest -q tests/ >/dev/null 2>&1; then ok "pytest tests/"; else bad "pytest tests/"; fi

# 5. no stale dev-wording markers in delivery docs (EXACT phrases only; intentional
#    integrity caveats like "공식 재현 아님" are deliberately NOT matched). docs/04
#    (describes pending rerun status) and docs/07 (release notes) are excluded — they
#    legitimately describe in-flight results / cleanup history.
DELIV="README.md docs/00-overview.md docs/01-quickstart.md docs/02-profiles-and-scoring.md docs/03-gsma-alignment-and-caveats.md docs/05-operations-and-troubleshooting.md docs/06-inl-handoff.md docs/08-results-manifest.md docs/presentation-prompt-ko.md docs/archive/README.md"
stale=$(grep -nE "TODO|진행 중|legacy default 승격" $DELIV 2>/dev/null || true)
if [ -z "$stale" ]; then ok "no stale markers in delivery docs"; else
  bad "stale markers in delivery docs"; echo "$stale" | sed 's/^/    /'; fi

# 6. no obvious secrets in tracked files (skip vendored harness + binaries; allow placeholders)
sec=$(git ls-files | grep -vE "^lm-evaluation-harness/" \
      | xargs grep -InE "hf_[A-Za-z0-9]{30,}|HF_TOKEN=[A-Za-z0-9]|HUGGINGFACE_TOKEN=[A-Za-z0-9]|api[_-]?key[\"']?[:=][\"']?[A-Za-z0-9]{16,}" 2>/dev/null || true)
if [ -z "$sec" ]; then ok "no obvious secrets in tracked files"; else
  bad "possible secret in tracked files"; echo "$sec" | sed 's/^/    /'; fi

# 7. no large tracked files (no model weights / cache / raw dumps)
if "$PY" scripts/check_tracked_file_sizes.py --max-mb 50 >/dev/null 2>&1; then ok "no tracked file > 50MB"; else
  bad "tracked file(s) > 50MB"; "$PY" scripts/check_tracked_file_sizes.py --max-mb 50 | sed 's/^/    /'; fi

# 8. docs internal links resolve (relative markdown links only; external/anchors skipped)
linkfail=$(
  while IFS= read -r f; do
    d=$(dirname "$f")
    grep -oE '\]\([^)]+\)' "$f" 2>/dev/null | sed -E 's/^\]\(//; s/\)$//' | while IFS= read -r t; do
      case "$t" in http*|\#*|mailto:*) continue;; esac
      t="${t%%#*}"; [ -z "$t" ] && continue
      [ -e "$d/$t" ] || echo "$f -> $t"
    done
  done < <(git ls-files '*.md')
)
if [ -z "$linkfail" ]; then ok "docs internal links resolve"; else
  bad "broken doc links"; echo "$linkfail" | sed 's/^/    /'; fi

# 9. info: bare group names must appear only as historical/guard/rename text
echo "INFO: bare open_telco_otlite/otfull occurrences (expected: historical/guard/rename only):"
grep -nE "open_telco_otlite\b|open_telco_otfull\b" README.md docs/*.md 2>/dev/null | sed 's/^/    /' || true

echo
if [ "$fail" -eq 0 ]; then echo "=== DELIVERY CHECK: PASS ==="; else echo "=== DELIVERY CHECK: FAIL ==="; exit 1; fi
