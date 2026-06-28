# 08 결과 매니페스트

이 문서는 **전달 산출물(evidence)의 위치·추적 여부·공유 안전성**을 정리한 매니페스트다.  
점수 수치의 단일 출처(single source of truth)는 `docs/04-final-results.md`이며, 본 매니페스트는 수치를 재기재하지 않는다.

> **공유 안전성**: tracked 항목은 공개 prompt/정답을 포함하지 않는 집계 결과(JSON)와 비교표(MD)다.  
> per-sample dump·raw log·model weight·HF cache는 추적 안 함·전달 안 함(아래 §제외 참조).

---

## 1. 산출물 위치 규칙

fresh rerun(10개 후보 모델 × {otlite, otfull}-gsma × 3회 반복) 결과는 아래 경로에 위치한다:

```
results/final/
  {otlite,otfull}-gsma-<model-key>/
    run1/   results_*.json
    run2/   results_*.json
    run3/   results_*.json
    _aggregate.json        # mean ± spread (aggregate_repeats.py 생성)
```

- **tracked 파일**: `results_*.json`(집계 결과) 및 `_aggregate.json`.  
- **비추적 파일**: `samples_*.jsonl`, `*.log`, `*.tmp`, `_logs/`, `_status.json` — `.gitignore`로 제외.  
- **완료(2026-06-29)**: 10개 모델 × {otlite, otfull} × 3회 = **20 trio / 60 result JSON, 0 실패**. 수치는 `docs/04-final-results.md`.

---

## 2. 핵심 수치 참조

점수 표·delta·모델별 분석은 `docs/04-final-results.md` 참조.  
공식 GSMA public 비교 기준: 7-task unweighted mean(집계 caveat 상세는 `docs/03-gsma-alignment-and-caveats.md`).

---

## 3. 추적 항목 (tracked)

| 구분 | 경로 | tracked | 공유 안전 |
|---|---|---|---|
| ot-lite_gsma fresh rerun (10종 × 3회) | `results/final/otlite-gsma-<key>/run{1,2,3}/results_*.json` + `_aggregate.json` | ✅ | ✅ |
| ot-full_gsma fresh rerun (10종 × 3회) | `results/final/otfull-gsma-<key>/run{1,2,3}/results_*.json` + `_aggregate.json` | ✅ | ✅ |

> 위 항목은 추적된다(2026-06-29 완료). 파일 크기 가드: `make delivery-check`(50MB/파일 초과 금지; 최대 결과 JSON ~40KB).

---

## 4. 제외 항목 (비추적·미전달)

| 항목 | 상태 | 사유 |
|---|---|---|
| `results/**/samples_*.jsonl`, `*.log`, `*.tmp` | 비추적·미전달 | per-sample dump·raw log (`.gitignore`) |
| model weights / HF cache (`~/.cache/huggingface`) | 비추적·미전달 | 대용량·라이선스, evidence 아님 |
| engineering-source의 `results/smoke-*/`, `results/conf-*/`, `*tp2-test*` | 미포함 | 진단/smoke run — 원본 저장소에 보존 |
| engineering-source의 `outputs/`, `chat/`, `lm-eval-ls-task` | 미포함 | 내부 개발 로그·실험 이력 — 원본 저장소에 보존 |
| engineering-source의 `EXPERIMENTS.md`, `PROGRESS.md`, `run-index.jsonl` | 미포함 | 개발 이력 문서 — `docs/archive/README.md` 연혁 요약으로 대체 |
| 비호환 모델(reasoning collapse artifact 해당) | 미포함 | `docs/04-final-results.md` §제외 모델 참조 |

---

## 5. 정합성 확인

- `make delivery-check`: tracked 파일 크기 게이트 + 금지 문구 grep 통과.
- `pytest tests/`: parser·smoke·결과 정합성 검증.
- 추적 JSON과 `docs/04-final-results.md` 수치가 일치함을 확인한 후 커밋한다.
