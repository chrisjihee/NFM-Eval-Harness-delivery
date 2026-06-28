# 02 — 프로파일·태스크·스코어링 계약

> 상세 정렬 caveat 및 격차 귀인은 [docs/03](03-gsma-alignment-and-caveats.md),
> 실측 결과 수치는 [docs/04](04-final-results.md) 참조.

---

## 1. 프로파일 표

| 프로파일 그룹 | 목적 | Leaderboard 비교 가능 | 집계 방식 |
|---|---|:---:|---|
| `open_telco_otlite_gsma` / `open_telco_otfull_gsma` | **기본/권장.** run-script 기본값. scorer가 공식 `gsma-evals` 소스와 정렬. | **O** (7-task unweighted mean 기준) | `weight_by_size: false` (unweighted) |
| `open_telco_otlite_mcgen` / `open_telco_otfull_mcgen` | MC 4종만 묶은 generation sensitivity 진단. | X (sensitivity 측정 전용) | 해당 없음 |
| `open_telco_otlite_lm_eval_baseline` / `open_telco_otfull_lm_eval_baseline` | Legacy loglikelihood baseline. 진단 전용, 보존. | **X** (집계방식 불일치, leaderboard 비교 부적합) | `weight_by_size: true` (sample-weighted) |
| `open_telco_otlite_core4_lm_eval_baseline` | Legacy 4-task MC 스타터 번들. 진단 전용. | X | sample-weighted |

> **절대 사용 금지 이름**: bare `open_telco_otlite` / `open_telco_otfull` —
> run-script가 `exit 2`로 즉시 거부한다. `_gsma` 또는 `_lm_eval_baseline`을 명시할 것.

---

## 2. 7개 태스크 요약

| Public 컬럼 | `_gsma` 태스크 (ot-lite) | Dataset | output\_type | Metric | Parser / 스코어 규칙 |
|---|---|---|---|---|---|
| `teleqna` | `open_telco_teleqna_mcgen` | `GSMA/ot-lite` | `generate_until` | `acc` | 자유 single-letter → 0-based int 비교 |
| `teletables` | `open_telco_teletables_mcgen` | `GSMA/ot-lite` | `generate_until` | `acc` | 자유 single-letter → 0-based int 비교 (표 미주입) |
| `oranbench` | `open_telco_oranbench_mcgen` | `GSMA/ot-lite` | `generate_until` | `acc` | 자유 single-letter → 0-based int 비교 |
| `srsranbench` | `open_telco_srsranbench_mcgen` | `GSMA/ot-lite` | `generate_until` | `acc` | 자유 single-letter → 0-based int 비교 |
| `telemath` | `open_telco_telemath_gsma` | `GSMA/ot-lite` | `generate_until` | `acc` | `\boxed{}` 마지막 매치 → `isclose(rel=0.01, abs=0.01)` + exact fallback |
| `telelogs` | `open_telco_telelogs_gsma` | `GSMA/ot-lite` | `generate_until` | `acc` | `\boxed{}` 마지막 → `extract_first_int` soft 비교 |
| `three_gpp` | `open_telco_3gpp_tsg_gsma` | `GSMA/ot-lite` | `generate_until` | `acc` | WG regex `([A-Z]+\d+(?:-[A-Z]+)?)` first-match, ignorecase |

ot-full은 `open_telco_full_*_mcgen` / `open_telco_full_*_gsma` 대응 태스크를 사용한다.

---

## 3. 생성형 3종 GSMA scorer 계약 요약

| 태스크 | max\_gen\_toks | until | Scorer 규칙 (공식 소스) | 비고 |
|---|---:|---|---|---|
| `telemath_gsma` | 1024 | `[]` | 마지막 `\boxed{number}` → `math.isclose(rel_tol=0.01, abs_tol=0.01)` + 비숫자 exact (`telemath.py:42-62`) | 공식 system-prompt를 단일 프롬프트로 결합(known micro-diff) |
| `telelogs_gsma` | 1024 | `[]` | `parse_boxed_answer` 마지막 매치 → `extract_first_int` vs target 첫 정수; 둘 다 존재·동일 시 정답 (`telelogs.py:41-54`) | `\boxed{}` 미출력 시 무조건 오답 → collapse 위험 |
| `3gpp_tsg_gsma` | 256 | `[]` | `WG_PATTERN=([A-Z]+\d+(?:-[A-Z]+)?)` **first-match** group(1) ignorecase vs raw answer (`three_gpp.py:12,30`) | WG token 미출력 시 무조건 오답 → collapse 위험; 256은 의도적 유지 |

> `telemath` / `telelogs`가 256에서 `\boxed{}` rate≈0.00으로 collapse한 이력이 있어 **1024로 상향**했다.
> `3gpp_tsg`는 WG 토큰이 짧아 256으로 충분 — parity 손실이 아니다.

---

## 4. MC 4종 engine 미정렬 — 가장 큰 격차 동인

`*_mcgen` 태스크는 **자유 single-letter `generate_until`** (`max_gen_toks: 8`, `until: ["\n"]`)을 사용한다.

공식 GSMA 스택은 **`multiple_choice(cot=False)` 제약 디코딩** + `choice()` scorer
(`target=chr(65+answer)` exact match)다. 이 두 engine은 **전혀 정렬되지 않는다.**

| 축 | 공식 (Inspect AI) | 우리 `*_mcgen` | legacy `*_lm_eval_baseline` |
|---|---|---|---|
| 디코딩 | 제약 디코딩 (constrained) | 자유 생성 (free) | loglikelihood |
| 스코어러 | `choice()` letter exact | 0-based int 비교 | loglikelihood rank |

MC 4종은 후보 격차의 지배적 기여 태스크다 (상세 수치: [docs/03](03-gsma-alignment-and-caveats.md)).
`*_mcgen` delta는 **generation-vs-constrained-decoding sensitivity 측정**이지 공식 재현이 아니다.

---

## 5. Collapse gate — HARD gate (smoke ≥ 0.30)

생성형 3종 중 `telelogs_gsma` / `3gpp_tsg_gsma`는 모델이 `\boxed{}` / WG token을 출력하지
않으면 soft scorer가 무조건 INCORRECT 처리하므로 점수가 ~0으로 collapse할 수 있다.

**절차:**

1. **smoke (LIMIT=20)** 먼저 실행 — `telemath`/`telelogs` `\boxed{}` 출력률 및 `3gpp` WG-token 매치율 측정.
2. 어느 하나라도 **< 0.30** → **full ot-full run BLOCK**.
3. 미달 태스크를 `*_gsma_hinted` 변형(gold 비노출 출력 형식 안내 1줄 추가)으로 LIMIT=20 재측정.
4. emission rate 회복 확인 후 **사용자 승인** 하에만 비교군으로 진행.

상세 절차: [docs/03 §Collapse gate](03-gsma-alignment-and-caveats.md) 및 원본 `GSMA_SCORING_CONTRACT.md §2.3`.
