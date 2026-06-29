# NFM-Eval-Harness-delivery

EleutherAI `lm-evaluation-harness` 기반으로 GSMA Open Telco 7개 통신 도메인 task를 실행하는 경량 평가 harness이며, NFM-LLM 후보 모델의 상대 비교와 public leaderboard 근접 검증을 목적으로 합니다.

> 이 저장소는 공식 GSMA stack(Inspect AI 기반)의 완전 재현이 **아닙니다**.
> 기본 `_gsma` profile은 GSMA **공개 scoring contract에 정렬**된 profile이며,
> 특히 객관식(Multiple Choice: MC)은 자유 generation engine을 써서 공식 제약 디코딩과는 약간 다를 수 있습니다.
> 자세한 내용과 한계는 [docs/03-gsma-alignment-and-caveats.md](docs/03-gsma-alignment-and-caveats.md).

## Quick Start

```bash
# 0) 환경 준비: 처음에는 단계적으로 나눠서 실행하기를 권장
./setup-pre.sh
./setup-main.sh   # torch/vllm/transformers 하드핀 설치
./setup-post.sh   # lm_eval 버전 고정 설치: uv pip install "lm_eval[hf,vllm]==0.4.12"

# 1) GPU 없이 task 로딩 검증
make smoke

# 2) 1-sample bounded run (파이프라인 확인; 기본 backend = vLLM)
LIMIT=1 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh

# 3) 대표 full run (기본 backend = vLLM, 기본 task = open_telco_otlite_gsma)
#    기본값으로 MAX_MODEL_LEN=8192 · GPU_MEMORY_UTILIZATION=0.9가 적용된다.
CONFIRM_FULL_RUN=1 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh

#    VM/NCCL 등 까다로운 호스트에서는 안정화 옵션을 명시한다.
CONFIRM_FULL_RUN=1 VLLM_VISIBLE_DEVICES=0 EXTRA_MODEL_ARGS=enforce_eager=True \
  MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh

# 3-alt) HF backend (경량/대체 경로) — 긴 생성형 입력을 left-truncation 하므로
#        telelogs 등 일부 생성형 task가 0점으로 collapse할 수 있다. 대표 측정은 vLLM 사용.
CONFIRM_FULL_RUN=1 BACKEND=hf MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh

# 4) 전달 readiness 점검 + 단위테스트 + 비교 스크립트
make delivery-check
pytest -q
python scripts/compare_gsma_leaderboard.py --help
```

자세한 설치·실행은 [docs/01-quickstart.md](docs/01-quickstart.md),
인수자 가이드는 [docs/06-inl-handoff.md](docs/06-inl-handoff.md)를 보세요.

최종 결과(10모델 × 2 profile × 3회 평균, 60 result JSON + 20 `_aggregate.json`)는
**`results/final/`**에 있으며, 표·분석은 [docs/04-final-results.md](docs/04-final-results.md),
산출물 매니페스트는 [docs/08-results-manifest.md](docs/08-results-manifest.md)입니다.

## 기본 profile = `_gsma`

run 스크립트의 기본 task는 `_gsma`이므로 **`TASKS`를 생략하면 GSMA-compatible
profile이 실행**됩니다(7-task **unweighted** 평균, public leaderboard 비교 가능).

| Profile | 목적 | leaderboard 비교 |
|---|---|---|
| `open_telco_otlite_gsma` / `open_telco_otfull_gsma` | GSMA 공개 scoring contract 정렬 (기본) | Yes |
| `open_telco_*_lm_eval_baseline` | 기존 lm-eval/loglikelihood baseline | No, diagnostic only |
| `open_telco_*_mcgen` | MC-only scoring sensitivity | Partial, diagnostic only |

- legacy `_lm_eval_baseline`은 **기본 실행 경로에 없습니다**(보존된 진단용). leaderboard 비교에 쓰지 마세요.

## 대표 full run / 백엔드

기본 backend는 **vLLM**이다(속도·안정성, 그리고 긴 생성형 입력을 left-truncation 하지 않음).
run 스크립트는 vLLM 기본값으로 `MAX_MODEL_LEN=8192`·`GPU_MEMORY_UTILIZATION=0.9`를 적용한다.
HF backend는 `BACKEND=hf`로 쓸 수 있으나 긴 입력을 truncation 하므로 대표 측정에는 권장하지 않는다.

```bash
# ot-full (기본 = open_telco_otfull_gsma, 기본 backend = vLLM)
CONFIRM_FULL_RUN=1 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otfull.sh

# 대형 모델 tensor parallel (vLLM)
CONFIRM_FULL_RUN=1 VLLM_VISIBLE_DEVICES=0,1 TENSOR_PARALLEL_SIZE=2 \
  MODEL_NAME=Qwen/Qwen2.5-32B-Instruct ./run_open_telco_otfull.sh
```

대형 모델 운영 변수(`MAX_MODEL_LEN`, `GPU_MEMORY_UTILIZATION`, `EXTRA_MODEL_ARGS` 등)는
[docs/05-operations-and-troubleshooting.md](docs/05-operations-and-troubleshooting.md).

## 결과 비교

```bash
python scripts/compare_gsma_leaderboard.py --profile gsma --model gemma3-4b \
  --local-result <result json> --out-md outputs/gemma3-4b-delta.md
```

> public 비교 기준은 lm-eval group acc가 아니라 **7-task unweighted average**입니다
> (sample-weighted group acc와 혼동 금지).

반복 실행 평균(3회 mean±spread)은 `scripts/aggregate_repeats.py`로 집계합니다.

## 문서 맵

| 문서 | 용도 |
|---|---|
| [docs/00-overview.md](docs/00-overview.md) | 한 장 개요(정체성·결론·한계) |
| [docs/01-quickstart.md](docs/01-quickstart.md) | 5분 quickstart |
| [docs/02-profiles-and-scoring.md](docs/02-profiles-and-scoring.md) | profile·task·scorer contract |
| [docs/03-gsma-alignment-and-caveats.md](docs/03-gsma-alignment-and-caveats.md) | GSMA 정렬·격차 분해·재현 caveat |
| [docs/04-final-results.md](docs/04-final-results.md) | 최종 rerun 결과표(mean±spread) |
| [docs/05-operations-and-troubleshooting.md](docs/05-operations-and-troubleshooting.md) | 환경·운영변수·장애 회피 |
| [docs/06-inl-handoff.md](docs/06-inl-handoff.md) | **인수자 시작점**·체크리스트 |
| [docs/07-release-notes.md](docs/07-release-notes.md) | 릴리스 노트·license posture |
| [docs/08-results-manifest.md](docs/08-results-manifest.md) | 전달 산출물 위치·공유 안전성 |
| [docs/archive/](docs/archive/) | 개발 연혁 요약·third-party vendor note |

## 라이선스

라이선스는 현재 **TBD**입니다. 사용 범위·third-party·미포함 항목은 [USAGE_SCOPE.md](USAGE_SCOPE.md),
릴리스/라이선스 posture는 [docs/07-release-notes.md](docs/07-release-notes.md) 참조.

## 범위

이 저장소는 내부 baseline harness입니다.
멀티모달/LMM/LAM, Planning, RAG, 한국어 QA 등은 범위 밖(2차 과제)입니다.
