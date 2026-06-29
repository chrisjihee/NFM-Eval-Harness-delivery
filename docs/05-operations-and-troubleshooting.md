# 05 — 운영 및 장애 대응

> 이 문서는 환경 설정부터 대형 모델 운영 변수, host-env(VM/NCCL/오프라인) 레시피, 알려진 장애 목록까지 다룬다.
> 수치·결과는 [docs/04-final-results.md](04-final-results.md) 참조. 이 문서에서 점수는 기술하지 않는다.

---

## 1. 환경 하드핀 (재현 필수)

| 항목 | 값 |
|---|---|
| Python | 3.12.13 |
| PyTorch | 2.11.0+cu128 (CUDA 12.8 wheel) |
| transformers | 5.12.1 |
| vLLM | 0.23.0 |
| lm-evaluation-harness (lm_eval) | `0.4.12` (PyPI; `uv pip install "lm_eval[hf,vllm]==0.4.12"`) |
| GPU | A100 40 GB × 6 |
| OS | Linux (GPU 서버) |
| 가상환경 관리 | `uv` / `.venv` |

다른 버전으로 설치하면 재현이 보장되지 않는다. 특히 vLLM 0.23.x는 CUDA forward-compat 처리가 setup-main.sh 안에 포함되어 있으므로, wheel을 직접 교체하지 않는다.

---

## 2. setup-*.sh 설치 절차

```bash
# GPU 서버 루트 디렉터리에서 순서대로 실행
./setup-pre.sh    # OS-level 의존성, uv 설치 여부 확인
./setup-main.sh   # .venv 생성, pyproject.toml 의존성 설치, vLLM runtime 검증
./setup-post.sh   # lm_eval 버전 고정 pip 설치, (선택) gsma-evals 참조 클론
```

### lm-evaluation-harness(lm_eval) 설치 상세

`setup-post.sh`는 lm_eval을 PyPI에서 버전 고정으로 설치한다:

```bash
uv pip install "lm_eval[hf,vllm]==0.4.12"
```

- `[hf,vllm]` extra가 hf·vllm 백엔드와 lm_eval 보조 의존성(sqlitedict, sacrebleu,
  pytablewriter, word2number, more_itertools, rouge-score)을 함께 설치한다 →
  별도 수동 설치 불필요.
- `setup-main.sh`가 먼저 torch/vllm/transformers 하드핀을 설치하므로, 이 명령은
  이미 만족된 핀을 변경하지 않는다(uv는 만족된 의존성을 다운그레이드하지 않음).
- 과거 engineering 트랙은 git clone 후 `-e ./lm-evaluation-harness --no-deps`로
  설치하고 SHA `97a5e2c7`(= `v0.4.12` 태그 +12 commits)를 핀했다. 전달본은 재현
  단순화를 위해 PyPI release `0.4.12`를 사용한다(대상 task 점수는 run-to-run 변동
  범위 내에서 동일하다).

lm_eval이 설치되었는지 확인:

```bash
.venv/bin/python -c "import lm_eval; print(lm_eval.__version__)"   # 0.4.12
# 미설치 시
.venv/bin/python -c "import lm_eval" || uv pip install "lm_eval[hf,vllm]==0.4.12"
```

### gsma-evals (선택, 참조 전용)

`setup-post.sh`가 `gsma-evals/` 하위에 공식 GSMA scorer repo를 선택적으로 클론한다.
이는 **런타임 의존성이 아니다** — `*_gsma` scorer 로직은 이미
`open_telco_lm_eval/tasks/**/utils.py`에 미러링되어 있고 task는 `--include_path`로
로드된다. gsma-evals는 공식 scorer 소스를 대조·확인하려는 경우에만 두며, 수동으로
편집하지 않는다(정렬 기준점이므로 원본 유지).

---

## 3. 환경 재현 검증

INL 인수 후 **빈 디렉터리에서 처음 설치하는 경우** 아래 순서로 from-scratch 경로를 검증한다:

```bash
./setup-pre.sh && ./setup-main.sh && ./setup-post.sh
make smoke    # GPU 없이 task YAML 로딩 검증 — green이면 설치 정상
```

`make smoke` green = lm-eval 설치 + task YAML 파싱 + 의존성 import 모두 정상.

> **검증(2026-06-29 설치 방식 갱신)**: 빈 디렉터리에 새로 clone → fresh `.venv` 생성 →
> `uv pip install -e .` → `setup-post.sh`의 `uv pip install "lm_eval[hf,vllm]==0.4.12"`
> → `make smoke`가 `OK: all requested tasks/groups loaded`로 통과한다(생성된
> `.venv/bin/activate`의 `VIRTUAL_ENV`가 새 clone 경로를 가리킴 = 정상 relocatable).
> 즉 symlink 없는 from-scratch 경로가 동작함이 검증되었다.

---

## 4. 대형 모델 운영 변수

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `MODEL_NAME` | (필수) | HuggingFace 모델 식별자 (예: `google/gemma-3-4b-it`) |
| `BACKEND` | `vllm` | `vllm`(기본/권장) 또는 `hf`(경량/대체; 긴 입력 left-truncation) |
| `DEVICE` | `cuda:0` | HF 백엔드 디바이스 |
| `BATCH_SIZE` | `auto` | HF 백엔드 배치 크기 |
| `VLLM_VISIBLE_DEVICES` | `0` | vLLM용 CUDA_VISIBLE_DEVICES |
| `GPU_MEMORY_UTILIZATION` | `0.9` | vLLM KV 캐시 메모리 비율 |
| `MAX_MODEL_LEN` | `8192` | vLLM 컨텍스트 길이 제한 (기본 8192; bundled task는 8192 미만이라 점수 영향 없음) |
| `TENSOR_PARALLEL_SIZE` | `1` | vLLM TP; 24–33B 모델은 `2` 사용 |
| `TASKS` | `open_telco_otlite_gsma` | 실행할 task 그룹 (생략 시 기본값 `_gsma`) |
| `LIMIT` | (미설정) | 샘플 수 상한 (smoke용; 생략 시 전체) |
| `CONFIRM_FULL_RUN` | (미설정) | `1`로 설정해야 전체 run 허용 |
| `EXTRA_MODEL_ARGS` | (미설정) | vLLM 추가 인자 (아래 참조) |
| `TELETABLES_ROOT` | (미설정) | legacy/superset 표 원본 경로. 기본 `_gsma`는 question+choices parity라 불필요; 미설정 시 legacy task만 metadata-only |

### 모델별 권장 EXTRA_MODEL_ARGS

| 모델 계열 | 추가 인자 | 이유 |
|---|---|---|
| Qwen3 계열 | `enable_thinking=False` | thinking 토큰 무한 출력 방지 (Qwen3 전용 vLLM 옵션) |
| Mistral 계열 | `tokenizer_mode=mistral` | Mistral tokenizer API 호환 |
| 24–33B 모델 | (tp=2로 별도 설정) | 단일 GPU 메모리 초과 방지 |

예시:

```bash
# Qwen3-32B (tp=2, thinking 비활성화)
BACKEND=vllm \
VLLM_VISIBLE_DEVICES=0,1 \
TENSOR_PARALLEL_SIZE=2 \
MAX_MODEL_LEN=8192 \
GPU_MEMORY_UTILIZATION=0.9 \
EXTRA_MODEL_ARGS="enable_thinking=False" \
CONFIRM_FULL_RUN=1 \
MODEL_NAME=Qwen/Qwen3-32B \
./run_open_telco_otlite.sh

# Mistral-7B
BACKEND=vllm \
VLLM_VISIBLE_DEVICES=0 \
EXTRA_MODEL_ARGS="tokenizer_mode=mistral" \
CONFIRM_FULL_RUN=1 \
MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3 \
./run_open_telco_otlite.sh
```

---

## 5. Host-env 레시피 (VM이 있는 호스트)

동일 노드에 VM이 떠 있으면 두 가지 문제가 발생한다:

- **NCCL 인터페이스 자동탐지 실패** → multi-GPU vLLM hang
- **vLLM in-process HF-hub 다운로드 hang** → 모델 로드 타임아웃

### 해결 절차

**Step 1: 모델 사전 다운로드** (vLLM 기동 전, Python에서 직접)

```python
from huggingface_hub import snapshot_download
snapshot_download(repo_id="google/gemma-3-4b-it", local_dir=None)
# 또는 캐시 기본 경로(~/.cache/huggingface)에 미리 받아두기
```

**Step 2: 오프라인 모드 + NCCL 인터페이스 고정**

```bash
export HF_HUB_OFFLINE=1          # vLLM 기동 시 HF hub 접근 차단
export NCCL_SOCKET_IFNAME=lo     # loopback으로 고정 (VM이 eth 인터페이스를 가로채는 경우)
export NCCL_IB_DISABLE=1         # InfiniBand 비활성화
```

**Step 3: vLLM 추가 안정화**

```bash
EXTRA_MODEL_ARGS="enforce_eager=True"  # CUDA graph 빌드 skip (메모리 절약 + 안정성)
MAX_MODEL_LEN=8192                     # 128K context 모델 KV 캐시 초과 방지
GPU_MEMORY_UTILIZATION=0.9
```

**Step 4: stale lock 정리 (강제종료 후)**

```bash
find ~/.cache/huggingface -name "*.lock" -delete
```

---

## 6. 알려진 장애 및 회피

### 6-1. Reasoning/Harmony 모델 MC collapse — artifact

**증상**: reasoning 모델(DeepSeek-R1-Distill 계열, gpt-oss 계열 등)이 객관식 태스크에서 0점에 가까운 점수.

**원인**: 이 모델들은 단답 letter 생성보다 장문 reasoning chain을 먼저 출력한다. 현재 MC parser는 첫 단일 문자를 추출하도록 설계되어 있어, reasoning 출력이 앞에 오면 추출 실패.

**회피**: MC 점수를 이 모델의 능력치로 해석하지 않는다. `EXTRA_MODEL_ARGS="enable_thinking=False"`는 Qwen3 전용이며, 일반 reasoning 모델에는 적용 불가. 생성형 태스크(`*_gsma` 중 telemath/telelogs/3gpp) 점수를 우선 참조한다.

### 6-2. Gemma3 128K context → KV 캐시 초과

**증상**: vLLM이 `max_model_len` 기본값(128K)으로 기동하면 A100 40GB에서 메모리 부족.

**회피**:

```bash
MAX_MODEL_LEN=8192 GPU_MEMORY_UTILIZATION=0.9
```

ot-lite/ot-full 최대 프롬프트 길이가 8192 토큰을 초과하지 않으므로 점수에 영향 없음.

### 6-3. vLLM import는 성공하나 generation 실패

**점검 순서**:

1. `version-vllm-check.log` 확인 — CUDA runtime 불일치 여부.
2. GPU 메모리 여유 확인 (`nvidia-smi`).
3. `GPU_MEMORY_UTILIZATION=0.5 MAX_MODEL_LEN=4096`으로 재시도.
4. 그래도 실패하면 `BACKEND=hf` fallback 사용.

### 6-4. HF gated 모델 접근 오류

```bash
huggingface-cli whoami          # 로그인 상태 확인
export HF_TOKEN=<your_token>    # 미인증 시 설정 (레포에 커밋 금지)
```

gemma, llama 계열은 HF 약관 수락 필요.

### 6-5. Left-truncation 경고

**증상**:
```
Left truncation applied. Original sequence length was 2902, truncating to last 2024 tokens.
```

**원인**: HF 백엔드의 모델 max length와 프롬프트 길이 충돌. telelogs, teletables, 3gpp 태스크에서 주로 발생.

**회피**: vLLM 백엔드 + `MAX_MODEL_LEN=8192` 사용. HF 백엔드에서는 `--model_args max_length=8192` 추가.

### 6-6. TeleTables 저점수

원본 표 파일 없이 실행하면 metadata-only로 평가된다:

```bash
export TELETABLES_ROOT=/path/to/extracted/TeleTables/tables
# 구조: $TELETABLES_ROOT/<document_id>/<table_id>/table.{md,html,json}
```

### 6-7. Out-of-memory (OOM)

```bash
# HF 백엔드
BACKEND=hf BATCH_SIZE=1 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh

# vLLM 백엔드
BACKEND=vllm GPU_MEMORY_UTILIZATION=0.5 MAX_MODEL_LEN=4096 \
  MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh
```

### 6-8. Public leaderboard 점수와 불일치

예상된 차이다. 공식 GSMA stack은 Inspect AI 기반, 이 harness는 lm-eval 기반이다.

비교 시 확인 사항:

- `_gsma` profile 사용 여부 (기본값, run script `TASKS` 생략 시 자동 적용)
- 비교 기준: **7-task unweighted task mean** (sample-weighted는 결과가 다름)
- 모델 variant 일치 여부 (예: `gemma3-4b-it` vs 공개 행의 `gemma3-4b`)
- MC는 자유 single-letter generation이므로 공식 제약 디코딩과 engine 미정렬

```bash
python scripts/compare_gsma_leaderboard.py \
  --profile gsma --model <leaderboard_key> \
  --local-result <result.json> \
  --out-md outputs/<key>-delta.md
```
