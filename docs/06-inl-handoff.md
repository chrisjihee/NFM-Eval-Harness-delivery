# 06 — INL 인수 가이드

> 지능네트워크연구실(INL) 인수자를 위한 시작점.
> 30분이면 이 harness가 무엇인지, 어떻게 돌리는지, 결과가 무슨 의미인지 파악할 수 있다.
> 정확한 수치·delta는 [docs/04-final-results.md](04-final-results.md) 참조. 이 문서에서 점수를 재기술하지 않는다.

---

## 1. 이 저장소가 무엇인가

ETRI Language Intelligence Lab의 **내부 NFM-LLM baseline harness**다.
EleutherAI **lm-evaluation-harness 기반**으로 GSMA Open Telco AI 7개 통신 도메인 태스크를 실행한다.

용도:
- NFM-LLM 후보 base 모델 및 도메인 적응 변형의 **상대 비교**
- GSMA 공개 leaderboard와 **비교 가능한 신뢰도** 확보

> **필독 caveat:** 공식 GSMA stack(Inspect AI 기반)의 완전 복제가 **아니다**.
> `_gsma` profile은 GSMA 공개 scoring contract에 정렬된 비교용 profile이다.
> MC(객관식) 4종은 자유 single-letter generation으로, 공식 제약 디코딩과 engine이 **미정렬**된 상태다.
> 상세는 [docs/03-gsma-alignment-and-caveats.md](03-gsma-alignment-and-caveats.md).

---

## 2. 설치

```bash
# GPU 서버 저장소 루트에서
./setup-pre.sh && ./setup-main.sh && ./setup-post.sh
```

- lm_eval: PyPI 버전 고정 설치 — `uv pip install "lm_eval[hf,vllm]==0.4.12"` (setup-post.sh)
- gsma-evals scorer repo: (선택) `setup-post.sh`가 참조용으로 클론 — 런타임 의존성 아님
- 환경 하드핀 및 재설치 SOP 전체: [docs/05-operations-and-troubleshooting.md](05-operations-and-troubleshooting.md)

---

## 3. 가장 먼저 — smoke + acceptance (약 30분)

```bash
# 1) GPU 없이 task YAML 로딩 검증
make smoke

# 2) 1-sample 파이프라인 (GPU 최소 사용)
LIMIT=1 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh

# 3) 전달 readiness 게이트 (문서·secret·용량·tree 검증)
make delivery-check
```

세 단계 모두 통과하면 기본 설치가 정상이다.

---

## 4. 대표 실행 (ot-lite / ot-full)

기본 backend는 vLLM이다(`MAX_MODEL_LEN=8192`·`GPU_MEMORY_UTILIZATION=0.9` 기본 적용).
HF backend(`BACKEND=hf`)는 경량/대체 경로이며 긴 생성형 입력을 left-truncation 하므로 대표 측정에는 vLLM을 쓴다.

```bash
# ot-lite_gsma 전체 실행 (기본 backend = vLLM)
CONFIRM_FULL_RUN=1 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh

# ot-full_gsma 전체 실행 (public 동일 split, 16,866 docs; 기본 backend = vLLM)
CONFIRM_FULL_RUN=1 VLLM_VISIBLE_DEVICES=0 \
  MODEL_NAME=google/gemma-3-4b-it \
  ./run_open_telco_otfull.sh
```

주의:
- bare `open_telco_otlite` / `open_telco_otfull`은 **실행 불가** (run script fail-fast).
  `TASKS` 생략 시 기본값 `_gsma`가 자동 적용된다.
- legacy lm-eval/loglikelihood baseline은 `*_lm_eval_baseline` suffix를 명시해야 한다 (diagnostic only).
- `CONFIRM_FULL_RUN=1` 없이 `LIMIT=N`만 쓰면 bounded smoke로 동작한다.

---

## 5. 결과 비교

비교 기준은 **7-task unweighted task mean** (sample-weighted 아님):

```bash
python scripts/compare_gsma_leaderboard.py \
  --profile gsma \
  --model <leaderboard_key> \
  --local-result <result_json> \
  --out-md outputs/<key>-delta.md
```

public과 local 수치 delta, 제외 모델 목록 등 상세 결과는 [docs/04-final-results.md](04-final-results.md) 참조.

---

## 6. 읽는 순서

| 순서 | 파일 | 내용 |
|---|---|---|
| 1 | [docs/00-overview.md](00-overview.md) | 저장소 개요, 목적, 구조 |
| 2 | [docs/01-quickstart.md](01-quickstart.md) | 빠른 시작, 설치, 첫 실행 |
| 3 | [docs/02-profiles-and-scoring.md](02-profiles-and-scoring.md) | task group, profile, scoring 방식 |
| 4 | [docs/03-gsma-alignment-and-caveats.md](03-gsma-alignment-and-caveats.md) | GSMA 정렬 범위, MC engine 미정렬, caveat |
| 5 | [docs/04-final-results.md](04-final-results.md) | 핵심 결과·수치·delta |
| 6 | [docs/05-operations-and-troubleshooting.md](05-operations-and-troubleshooting.md) | 환경 설정, 운영 변수, 장애 대응 |

---

## 7. 운영 주의

### HF token / gated 모델

gemma, llama 계열은 HuggingFace 약관 수락 + 토큰 필요:

```bash
huggingface-cli whoami        # 로그인 상태 확인
export HF_TOKEN=<your_token>  # 미인증 시 설정 (레포에 커밋 금지)
```

### vLLM / CUDA

- GPU 작업 전 `.venv` activate 필수 (run 스크립트가 자동 수행).
- vLLM import 성공 ≠ generation 성공. 실패 시 `version-vllm-check.log` 확인 후 `BACKEND=hf` fallback.

### NCCL / 오프라인 캐시 (VM이 있는 호스트)

동일 노드에 VM이 떠 있으면 NCCL 인터페이스 자동탐지와 vLLM in-process HF-hub 다운로드가 hang할 수 있다:

```bash
# 모델 사전 다운로드 (vLLM 기동 전)
python -c "from huggingface_hub import snapshot_download; snapshot_download('<model_id>')"

# 환경변수 설정
export HF_HUB_OFFLINE=1
export NCCL_SOCKET_IFNAME=lo
export NCCL_IB_DISABLE=1
```

강제종료 후에는 stale lock 정리:

```bash
find ~/.cache/huggingface -name "*.lock" -delete
```

상세: [docs/05-operations-and-troubleshooting.md §5](05-operations-and-troubleshooting.md)

### 데이터셋

로컬 캐시 없으면 첫 실행 시 HF에서 자동 다운로드 (`GSMA/ot-lite`, `GSMA/ot-full`).
오프라인 환경에서는 사전 다운로드 후 `HF_HUB_OFFLINE=1` 적용.

---

## 8. 알려진 caveat

- **공식 GSMA 완전 재현 아님**: engine 미정렬 (MC 자유 gen vs 공식 제약 디코딩). `_gsma`는 scoring contract 정렬이지 stack 동일 재현이 아니다.
- **Reasoning/Harmony 모델 MC collapse**: DeepSeek-R1-Distill 계열 등 reasoning 모델이 MC에서 0점에 가까운 점수를 내는 것은 모델 능력치가 아닌 **artifact**다. 생성형 태스크 점수 참조.
- **Gemma3 계열 emission 취약**: telemath/telelogs에서 `\boxed{}` 출력이 불안정해 생성형 점수가 저평가될 수 있다.
- **License**: 미정(TBD). 외부 배포 전 GSMA dataset / lm-eval / vLLM / 모델 라이선스와 별개로 결정 필요.

---

## 9. 인수 체크리스트

- [ ] `make smoke` green 확인 (task 로딩 정상)
- [ ] `LIMIT=1` acceptance 실행 성공 (1-sample 파이프라인 통과)
- [ ] `make delivery-check` 통과 (문서·secret·용량·tree 검증)
- [ ] [docs/04-final-results.md](04-final-results.md) 결과 검토
- [ ] HF token 및 gated 모델 접근 설정 완료
- [ ] 외부 배포 여부에 따른 license 결정 (내부 사용은 별도 조치 불필요)
- [ ] (선택) 신규 모델: ot-lite smoke → ot-full 순서로 확장
