# 03 — GSMA 정렬 현황 및 정직한 caveat

> 프로파일·스코어링 계약 상세는 [docs/02](02-profiles-and-scoring.md),
> 실측 결과 수치는 [docs/04](04-final-results.md) 참조.

---

## 1. 집계방식 정정 — 필수 선독

과거 문서에 기재된 "local 0.3718 vs public 0.397, 격차 약 2.5%p"는
**집계방식이 다른 두 값을 뺀 착시**다.

| 값 | 어디서 | 집계 방식 |
|---|---|---|
| local group acc `0.3718` | historical pre-rename run (`open_telco_otlite`, 현재 `open_telco_otlite_lm_eval_baseline`) | **sample-weighted** (`weight_by_size=True` fork default; teleqna 1000 sample이 지배) |
| public `0.397` | GSMA leaderboard (gemma3-4b) | **7-task unweighted mean** (컬럼 단순평균) |

이 두 값은 **직접 뺄 수 없다.** 올바른 동일 기준 비교:

| 기준 | local | public | delta |
|---|---:|---:|---:|
| 7-task unweighted mean | **0.259** | **0.397** | **−0.138 (약 −13.8%p)** |

`0.259`는 위 historical 7개 task 점수의 단순평균이다. 이 −13.8%p는 **후보 격차
(candidate gap)**이며 단정적 결론이 아니다 — 귀인은 §2에서 설명한다.

> `_gsma` 프로파일(`open_telco_otlite_gsma`)로 재실행한 Gemma 3 4B의 실측 수치는
> [docs/04](04-final-results.md) 참조 (public ≈0.397에 근접).

---

## 2. 격차 분해 — 후보 기여 및 귀인 caveat

### 2.1 태스크별 후보 격차 (historical baseline 기준)

| Benchmark | local (legacy) | public (gemma3-4b) | delta |
|---|---:|---:|---:|
| `teleqna` | 0.4500 | 0.6523 | −0.202 |
| `teletables` | 0.2000 | 0.2733 | −0.073 |
| `oranbench` | 0.3667 | 0.6600 | **−0.293** |
| `srsranbench` | 0.5467 | 0.7400 | **−0.193** |
| `telemath` | 0.0100 | 0.1367 | −0.127 |
| `telelogs` | 0.1700 | 0.1167 | **+0.053** |
| `three_gpp` | 0.0700 | 0.2000 | −0.130 |

> 출처: legacy `open_telco_otlite_lm_eval_baseline` historical run. `_gsma` 프로파일 재실행 수치는 [docs/04](04-final-results.md).

최대 기여: **MC 3종** (oranbench −0.293, teleqna −0.202, srsranbench −0.193).
`telelogs`는 local이 오히려 +0.053 우위.

### 2.2 격차의 구조적 요인 (귀인 미확정, 단정 금지)

| 요인 | 설명 | 기여 가능성 |
|---|---|---|
| **집계방식 차이** | sample-weighted vs unweighted (§1 참조) | 확정 (수치로 설명됨) |
| **MC scoring 방식** | loglikelihood(legacy) / 자유 생성(`*_mcgen`) vs 공식 제약 디코딩 | 최대 후보; MC 3종 지배 |
| **생성형 truncation** | HF run에서 left-truncation 2902→2024 tokens 다발 관찰 | 유력 후보 |
| **model variant 불일치** | public row = `gemma3-4b` (instruct/base/API/revision 미확인) | 미확인 |
| **dataset split 차이** | local `ot-lite` vs public 행의 실제 split | 미확인 |

**두 가지 입력이 현재 UNKNOWN이므로 원인 확정 불가:**
- 공식 GSMA leaderboard 점수 계산 시 정확한 추출·스코어링 방식.
- public row를 생성한 `gemma3-4b` variant (instruct / base / API-served / revision).

이 격차는 **관찰된 사실**이지 원인이 해명된 결론이 아니다.

---

## 3. Scorer-aligned vs engine-different 분리

`*_gsma` / `*_mcgen` 프로파일은 **공식 `gsma-evals` 코드(scorer)와 정렬을 시도**하지만
**완전 동일 재현이 아니다.** 이 둘을 항상 구분한다.

| Task 그룹 | Scorer 정렬 | Engine 정렬 | 핵심 비고 |
|---|---|---|---|
| MC 4종 (`*_mcgen`) | letter-match는 동치 | **미정렬** (자유 생성 vs 제약 디코딩) | **가장 큰 미정렬 축·지배 격차 동인** |
| `telemath_gsma` | **동일** (isclose 0.01 + exact fallback) | micro-diff (system-prompt 단일 결합) | scorer parity; prompt 결합은 known engine micro-diff |
| `telelogs_gsma` | **동일** (soft 첫 정수 비교) | 다름 (lm-eval `generate_until`) + collapse 위험 | HARD gate 대상 |
| `3gpp_tsg_gsma` | **동일** (WG regex first-match ignorecase) | 다름 (lm-eval `generate_until`) + collapse 위험 | HARD gate 대상; first-match 확정 |

### Collapse gate 요약

`telelogs` / `3gpp_tsg`에서 `\boxed{}` / WG token이 출력되지 않으면 soft scorer가
무조건 INCORRECT → 점수 collapse (~0). 절차:

- smoke (LIMIT=20) → emission rate 측정 → **< 0.30이면 full run BLOCK**.
- 미달 시 `*_gsma_hinted` 변형(gold 비노출 출력형식 안내 1줄)으로 재측정 후 사용자 승인.

상세: [docs/02 §5](02-profiles-and-scoring.md) 및 원본 `GSMA_SCORING_CONTRACT.md §2.3`.

---

## 4. "공식 재현 아님" 원칙 (절대 불변)

이 저장소는 **lm-eval 기반 내부 NFM-LLM baseline harness**다.

- 공식 GSMA 스택 = **Inspect AI** (lm-eval 아님); dataset은 동일(`GSMA/ot-lite` / `GSMA/ot-full`).
- `*_gsma` 프로파일은 **공개 scorer 코드(`gsma-evals/src/evals/*.py`) 정렬 시도**이지
  runtime / provider / model revision 동일 보장이 아니다.
- **"공식 GSMA leaderboard 완전 재현"을 주장하지 않는다.**
- generation 변형(`*_mcgen`, `*_gsma`)의 점수 상승을 **"공식 정렬"이라고 명명하지 않는다.**
- MC `*_mcgen` delta는 **generation-vs-constrained-decoding sensitivity 측정**으로만 다룬다.
- 남는 격차는 방법론 차이(집계방식 / split / prompt·scoring / Inspect AI stack / model variant)로
  정직하게 분해·문서화한다.

### 용인 가능 vs 불가

| 용인 가능 | 용인 불가 |
|---|---|
| local 결과가 public과 다르지만 원인 문서화 | "공식 재현" 주장 |
| task별 격차를 의심 원인과 함께 기록 | 격차를 숨기거나 축소 보고 |
| `_gsma`로 unweighted mean 비교 (caveat 포함) | `ot-lite`를 caveat 없이 public과 직접 비교 |
| parser/truncation 버그 수정 | 특정 모델 출력에만 맞춘 parser 과적합 |

---

## 5. Unweighted mean = leaderboard 관례 (공식 코드 미산출)

공식 `run_evals.py`는 7-task를 병렬 eval만 하고 **cross-task average를 계산하지 않는다.**
public leaderboard의 `average` 컬럼(예: gemma3-4b = 0.397)은 **7개 task 점수의 단순평균**으로
leaderboard UI가 표시하는 관례값이다.

`open_telco_otlite_gsma` / `open_telco_otfull_gsma` 그룹은 `weight_by_size: false`로
이 관례를 따른다. 이는 비교 편의를 위한 것이며 공식 계산의 일부라고 주장하지 않는다.
