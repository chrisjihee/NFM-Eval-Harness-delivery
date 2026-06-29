# Open Telco Tasks for NFM Evaluation Harness

This directory adds NFM-oriented Open Telco tasks on top of `lm-eval`.

## Naming policy

- **Default / recommended (leaderboard-comparable)**: `open_telco_otlite_gsma` /
  `open_telco_otfull_gsma`. These are the run-script defaults; their members are the
  `*_mcgen` (MC) and `*_gsma` (generation) tasks.
- **Legacy lm-eval baseline (preserved, diagnostic only)**: every former bare task/group
  now carries an `_lm_eval_baseline` postfix and is **not leaderboard-comparable**.
- **`*_mcgen`**: MC scoring-sensitivity diagnostic.
- Bare `open_telco_otlite` / `open_telco_otfull` are **non-runnable** (the run scripts
  fail-fast with `exit 2`); pick `_gsma` (recommended) or `_lm_eval_baseline` (legacy).

## Included tasks

### `ot-lite` packs

Recommended GSMA-compatible group (default): `open_telco_otlite_gsma`, with members:

- `open_telco_teleqna_mcgen`
- `open_telco_oranbench_mcgen`
- `open_telco_srsranbench_mcgen`
- `open_telco_teletables_mcgen`
- `open_telco_telemath_gsma`
- `open_telco_telelogs_gsma`
- `open_telco_3gpp_tsg_gsma`

Legacy lm-eval baseline (diagnostic only):

- `open_telco_teleqna_lm_eval_baseline`
- `open_telco_teletables_lm_eval_baseline`
- `open_telco_oranbench_lm_eval_baseline`
- `open_telco_srsranbench_lm_eval_baseline`
- `open_telco_3gpp_tsg_lm_eval_baseline`
- `open_telco_3gpp_tsg_gen_lm_eval_baseline`
- `open_telco_telemath_lm_eval_baseline`
- `open_telco_telelogs_lm_eval_baseline`
- `open_telco_otlite_lm_eval_baseline` group task
- `open_telco_otlite_core4_lm_eval_baseline` legacy 4-task group task

These tasks use the public `GSMA/ot-lite` dataset. `open_telco_otlite_gsma` is the
recommended 7-task leaderboard-comparable pack; `open_telco_otlite_lm_eval_baseline` is the
preserved 7-task loglikelihood baseline (diagnostic only); and
`open_telco_otlite_core4_lm_eval_baseline` preserves the original 4-task starter bundle.

### `ot-full` packs

Recommended GSMA-compatible group (default): `open_telco_otfull_gsma`, with members:

- `open_telco_full_teleqna_mcgen`
- `open_telco_full_oranbench_mcgen`
- `open_telco_full_srsranbench_mcgen`
- `open_telco_full_teletables_mcgen`
- `open_telco_full_telemath_gsma`
- `open_telco_full_telelogs_gsma`
- `open_telco_full_3gpp_tsg_gsma`

Legacy lm-eval baseline (diagnostic only):

- `open_telco_full_teleqna_lm_eval_baseline`
- `open_telco_full_teletables_lm_eval_baseline`
- `open_telco_full_oranbench_lm_eval_baseline`
- `open_telco_full_srsranbench_lm_eval_baseline`
- `open_telco_full_telemath_lm_eval_baseline`
- `open_telco_full_telelogs_lm_eval_baseline`
- `open_telco_full_3gpp_tsg_lm_eval_baseline`
- `open_telco_otfull_lm_eval_baseline` group task

These tasks use the public `GSMA/ot-full` dataset and mirror the 7 benchmark
columns exposed by the public `Open Telco AI Leaderboard`. Use `open_telco_otfull_gsma`
for leaderboard comparison; `open_telco_otfull_lm_eval_baseline` is diagnostic only.

## Run

The run scripts default to the recommended `open_telco_otlite_gsma` /
`open_telco_otfull_gsma` groups, so `TASKS` can be omitted:

```bash
./run_open_telco_otlite.sh
```

Override the default model if needed:

```bash
MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct ./run_open_telco_otlite.sh
```

Run a subset of the recommended `_gsma` tasks:

```bash
TASKS=open_telco_teleqna_mcgen,open_telco_oranbench_mcgen ./run_open_telco_otlite.sh
```

Run the legacy lm-eval baseline (diagnostic only, not leaderboard-comparable):

```bash
TASKS=open_telco_otlite_lm_eval_baseline ./run_open_telco_otlite.sh
```

Run the legacy 4-task starter pack (diagnostic only):

```bash
TASKS=open_telco_otlite_core4_lm_eval_baseline ./run_open_telco_otlite.sh
```

Run the 7-task `ot-full` pack (defaults to `open_telco_otfull_gsma`):

```bash
./run_open_telco_otfull.sh
```

The default backend is vLLM. Override the GPUs or model if needed:

```bash
VLLM_VISIBLE_DEVICES=3 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otfull.sh
```

`BACKEND=hf` selects the lightweight HF fallback, which left-truncates long
generation inputs (this can collapse generation tasks such as telelogs) — prefer
the default vLLM backend for faithful scoring.

Note: bare `open_telco_otlite` / `open_telco_otfull` are non-runnable; the run scripts
fail-fast (`exit 2`) and direct you to `_gsma` or `_lm_eval_baseline`.

## Notes

- `open_telco_otlite_gsma` (recommended) uses an unweighted mean
  (`weight_by_size: false`) of the 7 benchmark `acc` scores so it can be
  compared with the public leaderboard average. The legacy
  `open_telco_otlite_lm_eval_baseline` group is sample-weighted and diagnostic only.
- `open_telco_otlite_core4_lm_eval_baseline` preserves the previous 4-task setup,
  including the multiple-choice version of `3gpp_tsg`
  (`open_telco_3gpp_tsg_lm_eval_baseline`).
- `open_telco_3gpp_tsg_lm_eval_baseline` is the original multiple-choice convenience
  task (diagnostic only).
- `open_telco_3gpp_tsg_gen_lm_eval_baseline`, `open_telco_telemath_lm_eval_baseline`,
  and `open_telco_telelogs_lm_eval_baseline` use generation plus custom answer parsing.
- This is an MVP baseline harness, not a full reproduction of the official
  GSMA evaluation stack. The `_gsma` profile is scorer-aligned with the public
  `gsma-evals` source but is not an official reproduction (see
  `GSMA_SCORING_CONTRACT.md`).
- `open_telco_otfull_gsma` (recommended) uses an unweighted mean of the 7 benchmark
  `acc` scores to align with the public leaderboard average; the legacy
  `open_telco_otfull_lm_eval_baseline` group is sample-weighted and diagnostic only.
- `open_telco_full_3gpp_tsg_lm_eval_baseline`, `open_telco_full_telemath_lm_eval_baseline`,
  and `open_telco_full_telelogs_lm_eval_baseline` use generation plus custom answer
  parsing rather than raw string exact-match.
- `open_telco_full_teletables_lm_eval_baseline` works with the public `GSMA/ot-full`
  rows out of the box, and can inject original table content automatically when
  `TELETABLES_ROOT` points to the extracted `tables/<document_id>/<table_id>/`
  tree from the upstream `netop/TeleTables` release.
