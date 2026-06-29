#!/bin/bash
# 7. Install LM-Evaluation-Harness
source .venv/bin/activate
uv pip install "lm_eval[hf,vllm]==0.4.12"

# 8. Link HF cache and login to HF
shopt -s globstar
rm -f .cache_hf; ln -s ~/.cache/huggingface ./.cache_hf
hf auth whoami
hf auth login

# 9. Clone related repo (optional)
git clone https://github.com/EleutherAI/lm-evaluation-harness
git clone https://github.com/gsma-labs/evals gsma-evals
