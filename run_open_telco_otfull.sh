#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  echo "Missing virtual environment at ${ROOT_DIR}/.venv" >&2
  exit 1
fi

source "${ROOT_DIR}/.venv/bin/activate"

MODEL_NAME="${MODEL_NAME:-google/gemma-3-4b-it}"
BACKEND="${BACKEND:-hf}"
DEVICE="${DEVICE:-cuda:0}"
BATCH_SIZE="${BATCH_SIZE:-auto}"
TASKS="${TASKS:-open_telco_otfull_gsma}"
OUTPUT_PATH="${OUTPUT_PATH:-${ROOT_DIR}/results/${TASKS}}"

# Bare legacy group names were renamed (PR: GSMA default). Fail fast with guidance.
if [[ "${TASKS}" == "open_telco_otfull" || "${TASKS}" == "open_telco_otlite" ]]; then
  echo "ERROR: '${TASKS}' was renamed. For GSMA-leaderboard-comparable evaluation use" >&2
  echo "       open_telco_otfull_gsma (default; just omit TASKS). For the legacy" >&2
  echo "       lm-eval/loglikelihood baseline use open_telco_otfull_lm_eval_baseline." >&2
  exit 2
fi
DTYPE="${DTYPE:-bfloat16}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
DATA_PARALLEL_SIZE="${DATA_PARALLEL_SIZE:-1}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.7}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-}"
# Opt-in hf-backend context cap; unset by default (no behavior change). vllm
# uses MAX_MODEL_LEN above.
MAX_LENGTH="${MAX_LENGTH:-}"
VLLM_VISIBLE_DEVICES="${VLLM_VISIBLE_DEVICES:-${CUDA_VISIBLE_DEVICES:-}}"
LIMIT="${LIMIT:-}"
CONFIRM_FULL_RUN="${CONFIRM_FULL_RUN:-0}"

# GPU safety guard: refuse to launch an unbounded full GPU run unless explicitly
# confirmed. Set LIMIT=N for a bounded run, or CONFIRM_FULL_RUN=1 to allow a
# full run.
LIMIT_ARGS=()
if [[ -n "${LIMIT}" ]]; then
  LIMIT_ARGS=(--limit "${LIMIT}")
elif [[ "${CONFIRM_FULL_RUN}" != "1" ]]; then
  echo "full GPU run requires CONFIRM_FULL_RUN=1 (or set LIMIT=N for a bounded run)" >&2
  exit 2
fi

case "${BACKEND}" in
  hf)
    HF_MODEL_ARGS="pretrained=${MODEL_NAME}"
    if [[ -n "${MAX_LENGTH}" ]]; then
      HF_MODEL_ARGS="${HF_MODEL_ARGS},max_length=${MAX_LENGTH}"
    fi
    # Opt-in extra model_args passthrough (e.g. enable_thinking=False). No-op if unset.
    HF_MODEL_ARGS="${HF_MODEL_ARGS}${EXTRA_MODEL_ARGS:+,${EXTRA_MODEL_ARGS}}"

    lm_eval \
      --model hf \
      --model_args "${HF_MODEL_ARGS}" \
      --include_path "${ROOT_DIR}/open_telco_lm_eval/tasks" \
      --tasks "${TASKS}" \
      --device "${DEVICE}" \
      --batch_size "${BATCH_SIZE}" \
      --apply_chat_template \
      ${LOG_SAMPLES:+--log_samples} \
      ${LIMIT_ARGS[@]+"${LIMIT_ARGS[@]}"} \
      --output_path "${OUTPUT_PATH}"
    ;;
  vllm)
    if [[ -n "${VLLM_VISIBLE_DEVICES}" ]]; then
      export CUDA_VISIBLE_DEVICES="${VLLM_VISIBLE_DEVICES}"
    fi

    MODEL_ARGS="pretrained=${MODEL_NAME},dtype=${DTYPE},tensor_parallel_size=${TENSOR_PARALLEL_SIZE},data_parallel_size=${DATA_PARALLEL_SIZE},gpu_memory_utilization=${GPU_MEMORY_UTILIZATION}"
    if [[ -n "${MAX_MODEL_LEN}" ]]; then
      MODEL_ARGS="${MODEL_ARGS},max_model_len=${MAX_MODEL_LEN}"
    fi
    # Opt-in extra model_args passthrough (e.g. enable_thinking=False). No-op if unset.
    MODEL_ARGS="${MODEL_ARGS}${EXTRA_MODEL_ARGS:+,${EXTRA_MODEL_ARGS}}"

    lm_eval \
      --model vllm \
      --model_args "${MODEL_ARGS}" \
      --include_path "${ROOT_DIR}/open_telco_lm_eval/tasks" \
      --tasks "${TASKS}" \
      --batch_size "${BATCH_SIZE}" \
      --apply_chat_template \
      ${LOG_SAMPLES:+--log_samples} \
      ${LIMIT_ARGS[@]+"${LIMIT_ARGS[@]}"} \
      --output_path "${OUTPUT_PATH}"
    ;;
  *)
    echo "Unsupported BACKEND: ${BACKEND}. Use 'hf' or 'vllm'." >&2
    exit 1
    ;;
esac
