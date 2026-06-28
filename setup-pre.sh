#!/bin/bash
# 1. Install uv and python
curl -LsSf https://astral.sh/uv/install.sh | sh
$HOME/.local/bin/uv python install 3.12
$HOME/.local/bin/uv python update-shell
# exit
uv self update

# 2. Install CUDA toolkit (cf. https://developer.nvidia.com/cuda-12-8-0-download-archive)
wget https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda_12.8.0_570.86.10_linux.run
mkdir -p $HOME/.local/cuda-12.8
sh cuda_12.8.0_*.run --toolkit --toolkitpath=$HOME/.local/cuda-12.8 --defaultroot=$HOME/.local/cuda-12.8 --silent
ln -sfn $HOME/.local/cuda-12.8 $HOME/.local/cuda
cat >> ~/.bashrc <<'EOF'
# CUDA toolkit path
export CUDA_HOME="$HOME/.local/cuda"
export PATH="$CUDA_HOME/bin:$PATH"
EOF
# exit

# 3. Clone the repository (this slim INL delivery repo)
git clone https://github.com/chrisjihee/NFM-Eval-Harness-delivery.git
cd NFM-Eval-Harness-delivery
