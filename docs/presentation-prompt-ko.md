# 발표자료 생성 프롬프트 (중립 · Claude/GPT/Gemini 공용)

아래 프롬프트를 임의의 LLM에 그대로 붙여넣으면 12~15장 발표자료가 생성된다.
**2026-06-29 final rerun 실제 결과가 프롬프트 안(§final rerun 실제 결과 데이터)에 포함**되어 있어
별도 첨부 없이 바로 사용할 수 있다(원본 표·caveat은 [`docs/04-final-results.md`](04-final-results.md)).

---

## 프롬프트 (복사해서 사용)

당신은 통신 도메인 LLM 평가 프로젝트의 기술 발표자료를 만드는 전문가입니다.
아래 맥락을 바탕으로 **12~15장** 분량의 발표 슬라이드 개요를 작성하세요. 각 슬라이드는
제목 + 3~6개 bullet + (필요 시) 표/그림 placeholder로 구성합니다. 청중은 통신/AI 연구실
(지능네트워크연구실, INL)과 과제 관계자입니다. 한국어로 작성하고, 과장 없이 정직하게,
재현 한계를 명확히 표기하세요.

### 프로젝트 맥락
- 저장소: `NFM-Eval-Harness-delivery` — EleutherAI lm-evaluation-harness 기반 GSMA Open Telco
  7개 통신 도메인 task 평가 harness(내부 NFM-LLM baseline harness, 공식 GSMA stack 완전 재현 아님).
- 소속: ETRI 대형 국가 R&D "차세대 네트워크 AI 파운데이션 모델(NFM)". 언어 모델 평가 모듈은
  ETRI Language Intelligence Lab 담당, 본 전달 대상은 Intelligent Network Lab(INL).
- 목적: (1) NFM-LLM 후보 base 모델 간 상대 비교, (2) public GSMA leaderboard 점수에 근접해
  harness 신뢰도 확보(완전 동일 재현은 목표 아님 — 공식은 Inspect AI, 본 harness는 lm-eval).

### 반드시 포함할 12~15장 구성
1. 표지: 프로젝트/저장소 정체성, 한 줄 요약.
2. 배경: NFM 과제와 INL 전달 맥락, 이 harness의 역할(baseline harness, 공식 재현 아님).
3. GSMA Open Telco 7개 task 개요(teleqna/teletables/oranbench/srsranbench/telemath/telelogs/3gpp).
4. profile 체계: `_gsma`(기본, 공개 contract 정렬) vs `_lm_eval_baseline`(legacy 진단) vs `_mcgen`(MC 민감도).
5. GSMA alignment 과정: 공개 scoring contract에 scorer 정렬(telemath isclose 0.01 / telelogs soft first-int / 3gpp WG regex). "공식 완전 재현 아님" 명시.
6. 핵심 진단 — 격차의 정직한 분해: local group acc(sample-weighted) vs public(unweighted) **집계방식 정정**, 동일기준 비교 시 격차의 거의 전부가 **scoring 방식 + 집계 차이**. MC 미정렬이 지배 동인.
7. MC scoring: loglikelihood→generation 후 추출 시 public에 근접(단, 공식 추출 방식 UNKNOWN → `_mcgen` 비-default 유지, "공식 정렬" 주장 아님).
8. truncation / parser / TeleTables 해석 정정: 생성형 저점수는 truncation이 아니었음; parser robust화; TeleTables `_gsma`=question+choices=GSMA parity(저평가 아님).
9. legacy → gsma 정리: 이름 규칙(`_gsma` 기본화, legacy `_lm_eval_baseline`, bare name fail-fast)과 그 이유(처음 보는 사람 혼동 방지).
10. 모델 validation 결과(이전 패스): leaderboard 동일 split 재현(비-gemma3 계열이 public에 근접), reasoning/harmony 모델은 단답 MC와 비호환=artifact.
11. **final rerun 결과(2026-06-29)**: 10개 모델 × {ot-lite_gsma, ot-full_gsma} × **3회 반복 평균(mean±표준편차)**. 수치는 아래 **§final rerun 실제 결과 데이터** 표를 그대로 사용. leaderboard 모델은 public delta 병기.
12. 남은 한계: 공식 GSMA 완전 재현 아님(MC engine 미정렬이 최대 축), model-variant 불일치 가능성, 생성형 emission 취약 모델.
13. 환경/재현성: 하드핀(torch/vllm/transformers), lm_eval 버전 고정 설치(pip `0.4.12`) + (선택)gsma-evals 참조, 기본 backend=vLLM, host-env(VM/NCCL/offline) recipe, smoke→full→비교 절차.
14. INL가 받아서 할 일: setup→smoke→대표 full run→compare; 신규 모델 추가 절차(smoke 게이트→ot-lite→ot-full); 무결성 원칙(정답 누수/과적합 금지).
15. 마무리: 결론(harness 신뢰도 + 정직한 격차 분해) + 다음 단계(필요 시 후속 task 확장은 2차 과제).

### final rerun 실제 결과 데이터 (2026-06-29) — 슬라이드 11에 그대로 사용

10개 모델 × {ot-lite_gsma, ot-full_gsma} × 3회 반복(mean±표준편차, n=3, 0 실패).
public 비교는 동일 split인 **ot-full** 기준(`GSMA/leaderboard` 7-task unweighted mean).

| model | LB | ot-lite | ot-full | public | Δ(ot-full−pub) |
|---|:--:|---|---|---:|---:|
| google/gemma-3-4b-it | ✓ | 0.3956 | 0.3887 | 0.397 | −0.008 |
| Qwen2.5-7B-Instruct | ✓ | 0.4558 | 0.4479 | 0.4579 | −0.010 |
| Falcon3-10B-Instruct | ✓ | 0.4714 | 0.4620 | 0.4588 | +0.003 |
| gemma-3-12b-it | ✓ | 0.4357 | 0.4267 | 0.4638 | −0.037 |
| phi-4 | ✓ | 0.5279 | 0.4971 | 0.5045 | −0.008 |
| Mistral-Small-24B-Instruct-2501 | ✓ | 0.5078 | 0.4954 | 0.5163 | −0.021 |
| Qwen2.5-32B-Instruct | ✓ | 0.5068 | 0.5048 | 0.5067 | −0.002 |
| Qwen3-4B | — | 0.4530 | 0.4368 | (non-LB) | — |
| Qwen3-14B | — | 0.4644 | 0.4623 | (non-LB) | — |
| Qwen3-30B-A3B-Instruct-2507-FP8 | — | 0.4707 | 0.4629 | (non-LB) | — |

핵심 메시지(슬라이드 11):
- leaderboard 7종 중 gemma3-12b 제외 **6종 |Δ| ≤ 0.021(평균 0.009)** → public 근접 재현. delta 부호 +/− 혼재(억지 정렬 아님).
- reference anchor gemma-3-4b-it: ot-full 0.3887 ≈ public 0.397.
- gemma-3-12b만 −0.037: telemath/telelogs emission 취약(생성형 약함) 때문, 능력 저하 아님.
- 제외 모델: gpt-oss-20b(harmony), DeepSeek-R1-Distill-14B(always-reasoning), gemma-4-E4B(토크나이저), Qwen3.6-27B-FP8(다운로드 실패) — collapse = engine 비호환 artifact.
- 무결성: "공식 GSMA 재현" 아님, MC 4종은 자유 generation engine으로 공식 제약 디코딩과 미정렬.

### 작성 규칙
- 수치는 위 **§final rerun 실제 결과 데이터** 표에서만 인용하고 임의 생성 금지.
- 모든 점수 비교는 **7-task unweighted task mean** 기준임을 명시(sample-weighted와 혼동 금지).
- "공식 GSMA 재현" 같은 과장 표현 금지. "공개 scoring contract에 정렬된 내부 baseline harness"로 표기.
- 각 슬라이드 하단에 출처 문서(docs/0N) 1줄 표기.

---

> 사용법: 위 "프롬프트" 블록 전체 + `docs/04-final-results.md` / `docs/08-results-manifest.md` 표를
> 함께 LLM에 입력하면 12~15장 슬라이드 개요가 생성된다. 생성 후 수치·캡션을 docs/04와 대조 검수한다.
