#!/bin/bash
# 7. Install lm-evaluation-harness (lm_eval) — version-pinned from PyPI.
# The [hf,vllm] extras pull both backends plus lm_eval's helper deps (sqlitedict,
# sacrebleu, pytablewriter, word2number, more_itertools, rouge-score), so no
# separate manual install is needed. setup-main.sh already installed the
# hard-pinned torch/vllm/transformers, so those already-satisfied pins are left
# untouched by this command.
source .venv/bin/activate
uv pip install "lm_eval[hf,vllm]==0.4.12"

# 8. Link HF cache and login to HF
shopt -s globstar
rm -f .cache_hf; ln -s ~/.cache/huggingface ./.cache_hf
hf auth whoami
hf auth login

# 9. (optional) Clone gsma-evals for scorer-contract reference only.
# This is NOT a runtime dependency: the *_gsma scorers are mirrored in
# open_telco_lm_eval/tasks/**/utils.py and tasks load via --include_path. Clone
# only to inspect the official GSMA scorer source; do not edit it (it is the
# alignment reference). lm_eval itself is installed via pip in step 7 above.
git clone https://github.com/gsma-labs/evals gsma-evals
