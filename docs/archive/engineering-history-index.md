# Engineering History Index

This delivery repository intentionally does **not** include raw chat logs or historical
debug logs. Only an index/summary is kept here.

## Repository roles
- `NFM-Eval-Harness`: engineering source and provenance companion.
- `NFM-Eval-Harness-delivery`: curated handoff package for INL (this repository).

## Why raw history is not copied here
The engineering repository contains iterative development logs, Claude Code
conversations, experimental outputs, and intermediate debugging context. Those are
useful for provenance but are not the recommended onboarding path for non-author users.

This delivery repository keeps only:
- final runnable code
- minimal tests
- minimal scripts
- curated final results (`results/final/`)
- handoff documentation (`docs/`)
- this small archive index

## Milestone summary
- PR #1: packaging, guardrails, initial diagnosis (gap = aggregation artifact).
- PR #2: GSMA public scoring contract alignment (`*_gsma` profile).
- PR #3: naming / default-path cleanup (`*_gsma` default, legacy `*_lm_eval_baseline`, bare-name fail-fast).
- PR #4: model validation + TeleTables/TeleMath cleanup.
- PR #5: extended candidate validation + ot-full full-split results.
- PR #6: delivery packaging + fresh rerun bundle (in the engineering repo).
- Delivery repo: this curated handoff repository was created from the engineering repo,
  with a fresh 10-model × 2-profile × 3-repeat rerun under `results/final/`.

## Handoff principle
Use this delivery repository as the canonical handoff package. Use the engineering
repository only when detailed provenance is needed.
