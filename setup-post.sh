#!/bin/bash
# 7-1. Clone LM-Evaluation-Harness (for Task Execution), pinned to the validated SHA
git clone https://github.com/EleutherAI/lm-evaluation-harness
( cd lm-evaluation-harness && git checkout 97a5e2c710e2b56b9dd48f367bb6fe87bbb2c176 )

# 7-2. Clone GSMA-Evals (for Task Implementation)
git clone https://github.com/gsma-labs/evals gsma-evals

# 8. Link HF cache and login to HF
shopt -s globstar
rm -f .cache_hf; ln -s ~/.cache/huggingface ./.cache_hf

source .venv/bin/activate

# 9. Install LM-Evaluation-Harness into the venv (required before any evaluation).
#    --no-deps keeps the hard-pinned torch / vllm / transformers / datasets from
#    pyproject.toml from being overwritten; the extra packages are lm-eval core deps
#    that pyproject.toml does not already provide. Without this step `import lm_eval`
#    and every run fail.
uv pip install -e ./lm-evaluation-harness --no-deps
uv pip install sqlitedict sacrebleu pytablewriter word2number more_itertools rouge-score
python -c "import lm_eval; print('lm_eval installed:', lm_eval.__version__)"

# 10. Hugging Face login (for gated models such as gemma/llama)
hf auth whoami
hf auth login
