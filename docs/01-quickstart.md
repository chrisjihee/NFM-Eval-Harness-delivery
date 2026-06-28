# 빠른 시작 (5분)

> **provenance**: 원본 저장소 `NFM-Eval-Harness` HEAD `3954cac` 기준 slim화 전달본.

---

## 1단계 — 환경 준비

```bash
./setup-pre.sh && ./setup-main.sh && ./setup-post.sh
```

- lm-evaluation-harness를 pin SHA `97a5e2c7`로 clone하고 `.venv`를 구성한다.
- GPU 서버에서 실행한다. 환경 핀(Python 3.12.13 / torch 2.11.0+cu128 / vLLM 0.23.0) 및
  재설치 SOP는 `docs/05-operations-and-troubleshooting.md` 참조.

---

## 2단계 — GPU 없이 task 로딩 검증

```bash
make smoke
```

GPU 없이 7개 task YAML의 로딩·파서를 검증한다. 실제 추론 없이 설정 오류를 조기에 잡는다.

---

## 3단계 — bounded run (파이프라인 확인)

```bash
# 1-sample HF backend (파이프라인 통합 확인용)
LIMIT=1 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh
```

- `LIMIT=N`은 full run 가드 없이 N개 sample만 실행한다.
- `--apply_chat_template`는 run 스크립트가 항상 ON으로 적용한다.
- 기본 task = `open_telco_otlite_gsma` (TASKS 생략 시 자동).

---

## 4단계 — 대표 full run

### HF backend (ot-lite, 기본/권장)

```bash
CONFIRM_FULL_RUN=1 MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otlite.sh
```

- 기본 task = `open_telco_otlite_gsma` (7-task, ot-lite 1,700 docs).
- `CONFIRM_FULL_RUN=1`이 없으면 run 스크립트가 거부한다.

### vLLM backend + tensor parallel (ot-full, 대형 모델 권장)

```bash
CONFIRM_FULL_RUN=1 BACKEND=vllm VLLM_VISIBLE_DEVICES=0,1 TENSOR_PARALLEL_SIZE=2 \
  MODEL_NAME=google/gemma-3-4b-it ./run_open_telco_otfull.sh
```

- ot-full = 16,866 docs, public leaderboard와 동일 split.
- GPU 작업 전 `.venv` activate 필수(run 스크립트가 자동 수행).

> bare `open_telco_otlite` / `open_telco_otfull`은 실행 불가 — run 스크립트가
> fail-fast `exit 2`로 거부한다. `_gsma` 또는 `_lm_eval_baseline`을 명시할 것.

---

## 5단계 — 결과 비교

```bash
python scripts/compare_gsma_leaderboard.py \
  --profile gsma \
  --model gemma3-4b \
  --local-result <result_json_경로> \
  --out-md outputs/gemma3-4b-otlite-gsma-delta.md
```

- 비교 기준은 **7-task unweighted task mean** vs public unweighted이다.
  sample-weighted group acc와 혼동하지 말 것.
- 결과 JSON 경로 예: `results/otlite-gsma-gemma3-4b/results_*.json`

sanity anchor: gemma-3-4b-it ot-lite_gsma `≈ 0.399` ≈ public `0.397`.

---

## 6단계 — 전달 readiness 점검

```bash
make delivery-check
```

문서 존재 여부, 금지 문구(stale phrase) 부재, 비밀 파일 없음, 대용량 파일 없음,
결과 tree를 grep 기반으로 점검한다.

---

## 더 읽기

| 문서 | 내용 |
|---|---|
| [docs/02-profiles-and-scoring.md](02-profiles-and-scoring.md) | profile 상세, scoring contract, YAML 구조 |
| [docs/03-gsma-alignment-and-caveats.md](03-gsma-alignment-and-caveats.md) | public 비교 caveat, 격차 분해, MC engine 미정렬 |
| [docs/05-operations-and-troubleshooting.md](05-operations-and-troubleshooting.md) | 대형 모델 운영 변수, NCCL/HF-hub hang 대처, 알려진 장애 |
| [docs/06-inl-handoff.md](06-inl-handoff.md) | INL 인수자 가이드 — 30분 acceptance test, 체크리스트 |
