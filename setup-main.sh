#!/bin/bash
set -e
VENV_DIR=${VENV_DIR:-.venv}
CUDA_VERSION=${CUDA_VERSION:-128}
PYTHON_VERSION=${PYTHON_VERSION:-3.12}
echo -e "Starting environment setup with the following configuration:\n"
echo -e "VENV_DIR              : $VENV_DIR"
echo -e "CUDA_VERSION          : $CUDA_VERSION"
echo -e "PYTHON_VERSION        : $PYTHON_VERSION"
echo -e ""

TORCH_WHL_URL=${TORCH_WHL_URL:-https://download.pytorch.org/whl/cu${CUDA_VERSION}}
VLLM_RUNTIME_LIB_DIR="$PWD/${VENV_DIR}/lib/python${PYTHON_VERSION}/site-packages/nvidia/cu13/lib"
echo -e "TORCH_WHL_URL         : $TORCH_WHL_URL"
echo -e "VLLM_RUNTIME_LIB_DIR  : $VLLM_RUNTIME_LIB_DIR"

# --- CUDA forward-compatibility -------------------------------------------------
# vLLM wheels (>=0.20) are CUDA-13 builds: their .so NEED libcudart.so.13 / libnvrtc.so.13.
# On a host whose NVIDIA driver only supports CUDA 12.x (e.g. 570.x / CUDA 12.8), LLM().generate()
# fails with "CUDA driver version is insufficient for CUDA runtime version". NVIDIA Forward
# Compatibility (data-center GPUs such as A100) provides a *userspace* libcuda that runs the
# CUDA-13 runtime on top of the older kernel-mode driver. We vendor it (no root) and put it on
# LD_LIBRARY_PATH ahead of the cu13 runtime so libcuda.so.1 resolves to the forward-compat driver.
CUDA_COMPAT_DIR=${CUDA_COMPAT_DIR:-$HOME/.local/cuda-compat-13.3}
CUDA_COMPAT_DEB=${CUDA_COMPAT_DEB:-cuda-compat-13-3_610.43.02-1ubuntu1_amd64.deb}
CUDA_COMPAT_REPO=${CUDA_COMPAT_REPO:-https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64}
echo -e "CUDA_COMPAT_DIR       : $CUDA_COMPAT_DIR"

ensure_cuda_compat() {
    if [[ -e "$CUDA_COMPAT_DIR/libcuda.so.1" ]]; then
        echo "CUDA forward-compat present: $CUDA_COMPAT_DIR"; return 0
    fi
    echo "Setting up CUDA forward-compat at $CUDA_COMPAT_DIR ..."
    local tmp; tmp=$(mktemp -d)
    if curl -fsSL -o "$tmp/$CUDA_COMPAT_DEB" "$CUDA_COMPAT_REPO/$CUDA_COMPAT_DEB"; then
        ( cd "$tmp" && dpkg-deb -x "$CUDA_COMPAT_DEB" ex ) \
            && mkdir -p "$CUDA_COMPAT_DIR" \
            && cp -a "$tmp"/ex/usr/local/cuda-*/compat/. "$CUDA_COMPAT_DIR"/ \
            && echo "CUDA forward-compat installed: $(ls "$CUDA_COMPAT_DIR"/libcuda.so.* 2>/dev/null | head -1)"
    else
        echo "[WARN] could not download $CUDA_COMPAT_DEB ; forward-compat skipped (vLLM may fail on older drivers)"
    fi
    rm -rf "$tmp"
}


# 4. Create a new environment
t0=$SECONDS; echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] Creating new environment..."
    deactivate 2>/dev/null || true; rm -rf "${VENV_DIR}"; rm -rf *.egg-info;
    uv venv "${VENV_DIR}" --python "${PYTHON_VERSION}" --python-preference only-managed --clear
    source "${VENV_DIR}/bin/activate"
    uv pip list
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Created new environment (Elapsed: $((SECONDS - t0))s)"


# 5-0. Install build tools
t0=$SECONDS; echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] Installing build tools..."
    uv pip install -U cmake ninja wheel packaging setuptools setuptools_scm setuptools_rust
echo "[$(date +'%Y-%m-%d %H:%M:%S')] build tools installed (Elapsed: $((SECONDS - t0))s)"


# 5-1. Install the required packages: pyproject.toml
t0=$SECONDS; echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] Installing main project dependencies..."
    cat pyproject.toml
    uv pip install -U -e . \
    --extra-index-url "${TORCH_WHL_URL}" \
    --index-strategy unsafe-best-match
echo "[$(date +'%Y-%m-%d %H:%M:%S')] main project dependencies installed (Elapsed: $((SECONDS - t0))s)"


# 5-2. Configure runtime libraries: vllm (+ CUDA forward-compat)
t0=$SECONDS; echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] Configuring vllm runtime libraries..."
    ensure_cuda_compat
    # cu13 runtime first, then forward-compat libcuda PREPENDED so libcuda.so.1 resolves to it.
    export LD_LIBRARY_PATH="${VLLM_RUNTIME_LIB_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
    export LD_LIBRARY_PATH="${CUDA_COMPAT_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
    cat >> "${VENV_DIR}/bin/activate" <<EOF

# Added by setup-main.sh for vLLM wheel runtime libraries.
_VLLM_RUNTIME_LIB_DIR="\$VIRTUAL_ENV/lib/python${PYTHON_VERSION}/site-packages/nvidia/cu13/lib"
if [[ -d "\$_VLLM_RUNTIME_LIB_DIR" ]]; then
    export LD_LIBRARY_PATH="\$_VLLM_RUNTIME_LIB_DIR\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}"
fi
unset _VLLM_RUNTIME_LIB_DIR
# CUDA forward-compat libcuda (lets CUDA-13 vLLM run on a CUDA-12.x driver). Prepended so the
# forward-compat libcuda.so.1 is found before the system driver's.
_CUDA_COMPAT_DIR="${CUDA_COMPAT_DIR}"
if [[ -e "\$_CUDA_COMPAT_DIR/libcuda.so.1" ]]; then
    export LD_LIBRARY_PATH="\$_CUDA_COMPAT_DIR\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}"
fi
unset _CUDA_COMPAT_DIR
EOF
    echo -e "========================================"
    echo -e " * Tail of ${VENV_DIR}/bin/activate"
    echo -e "========================================"
    tail -n 11 ${VENV_DIR}/bin/activate
    echo -e "========================================"
echo "[$(date +'%Y-%m-%d %H:%M:%S')] vllm runtime libraries configured (Elapsed: $((SECONDS - t0))s)"


# 6. Check the installed packages and their versions
t0=$SECONDS; echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] Checking installed packages and versions..."
source "${VENV_DIR}/bin/activate"
uv pip list > version-dep.txt
uv pip list | grep -E "torch|trl|transformer|accelerate|llm|deepspeed|attn|peft|bitsandbytes|huggingface|datasets|pandas|numpy|chris|prog"

echo -e "\nChecking runtime imports for essential packages..."python - <<'PY'
import torch, torchaudio, torchvision
print("* torch         :", torch.__version__, " (cuda version:", torch.version.cuda, ")")
print("* torchaudio    :", torchaudio.__version__)
print("* torchvision   :", torchvision.__version__)
print("* cuda available:", "Yes" if torch.cuda.is_available() else "No")
if torch.cuda.is_available():
    print("  - cuda devices:", ', '.join([torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]))
    print("  - cuda tensor :", torch.tensor([1.0], device="cuda"))

import trl
from trl import SFTTrainer
print("* trl           :", trl.__version__, "\t-> import trl.SFTTrainer [OK]")

import vllm
from vllm import LLM
print("* vllm          :", vllm.__version__, "\t-> import vllm.LLM [OK]")
PY

# vLLM GENERATION check (NOT just import). Import success does not prove CUDA kernels/generate work;
# on a CUDA-12.x driver the CUDA-13 vLLM only works via the forward-compat libcuda configured above.
if [[ "${VLLM_GENERATE_CHECK:-1}" == "1" ]]; then
    echo -e "\nChecking vLLM GENERATION (real LLM.generate, not just import)..."
    VLLM_CHECK_MODEL=${VLLM_CHECK_MODEL:-meta-llama/Llama-3.1-8B-Instruct}
    if python check_vllm_runtime.py --model "$VLLM_CHECK_MODEL" \
            --max-model-len 2048 --gpu-memory-utilization 0.85 --enforce-eager \
            > version-vllm-check.log 2>&1; then
        echo "* vllm generate : [OK]  real LLM.generate succeeded (see version-vllm-check.log)"
    else
        echo "* vllm generate : [FAIL] import may pass but generate failed — inspect version-vllm-check.log"
        echo "                  (if 'driver insufficient for runtime', ensure CUDA forward-compat at \$CUDA_COMPAT_DIR)"
    fi
fi

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Checked installed packages and versions (Elapsed: $((SECONDS - t0))s)"
