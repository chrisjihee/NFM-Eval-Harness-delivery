# Usage Scope

This repository is an internal research handoff package for INL.

## Purpose
- Provide a reproducible local harness for GSMA Open Telco benchmark style evaluation.
- Provide curated final results and documentation for handoff.
- Provide the scripts and tests needed to smoke-test and inspect the package.

## Included
- Source code and task configuration (`open_telco_lm_eval/tasks/**`)
- Minimal scripts (`scripts/`) and minimal tests (`tests/`)
- Documentation (`docs/`)
- Curated final result JSON files under `results/final/`

## Not included
- Model weights
- Hugging Face cache
- Raw sample dumps
- Large debug logs
- Historical chat logs (kept only in the engineering/provenance repository)

## Third-party components
- Upstream licenses remain with their original projects, datasets, and model providers.
- This package uses or references upstream projects such as lm-evaluation-harness,
  GSMA evals, Hugging Face datasets/models, vLLM, and related dependencies.

## Important caveat
- This repository does **not** claim complete reproduction of the official GSMA
  Inspect AI production stack.
- It provides a local lm-eval based harness **aligned with the public GSMA scoring
  contract** as documented in `docs/02-profiles-and-scoring.md` and
  `docs/03-gsma-alignment-and-caveats.md`. In particular the multiple-choice tasks use a
  free-generation engine that is intentionally unaligned with the official
  constrained-decoding path.

## Repository license
- **TBD by the repository owner.** No license file is included yet; until a license is
  chosen, no redistribution rights are granted beyond internal INL handoff use.
