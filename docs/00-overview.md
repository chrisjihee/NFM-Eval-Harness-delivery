# NFM-Eval-Harness 개요

> **provenance**: 원본 저장소 `NFM-Eval-Harness` HEAD `3954cac` 기준 slim화 전달본.

---

## 저장소 정체성과 목적

이 저장소는 ETRI Language Intelligence Lab이 관리하는
**내부 NFM-LLM baseline harness**이다. EleutherAI **lm-evaluation-harness**를
기반으로 GSMA Open Telco AI 7개 통신 도메인 태스크를 실행한다.

목적은 두 가지다.

1. NFM-LLM 후보 base 모델과 도메인 적응 변형을 통신 도메인 LLM 태스크에서
   **상대 비교**하고 도메인 적응 효과를 측정한다.
2. GSMA 공개 leaderboard 점수에 **가능한 한 근접**하여 harness 신뢰도를 확보한다.

> **필독 — 정체성 한계.** 공식 GSMA leaderboard stack(Inspect AI 기반)의
> 완전 복제가 아니다. `_gsma` profile은 **GSMA 공개 scoring contract에
> 정렬**된 비교용 profile이며, "공식 GSMA 완전 재현"을 주장하지 않는다.

---

## 무엇을 측정하는가 — 7개 통신 도메인 태스크

| 태스크 | 유형 | 설명 |
|---|---|---|
| `teleqna` | MC (객관식) | 통신 도메인 QA |
| `oranbench` | MC (객관식) | O-RAN 아키텍처 지식 |
| `srsranbench` | MC (객관식) | srsRAN 설정·운용 지식 |
| `teletables` | MC (객관식) | 통신 표준 표 기반 추론 |
| `telemath` | 생성형 | 수식·수치 계산 |
| `telelogs` | 생성형 | 로그 라벨 분류 |
| `3gpp_tsg` | 생성형 | 3GPP TSG WG 분류 |

데이터셋 split: ot-lite 1,700 docs / ot-full 16,866 docs.
비교 기준은 항상 **7-task unweighted task mean**이다(sample-weighted group acc와 혼동 금지).

---

## Profile 개요

| Profile | 이름 | 목적 | leaderboard 비교 |
|---|---|---|---|
| **기본/권장** | `open_telco_otlite_gsma` / `open_telco_otfull_gsma` | GSMA 공개 scoring contract 정렬 | Yes — unweighted task mean |
| legacy (진단 전용) | `open_telco_otlite_lm_eval_baseline` / `…otfull…` | 기존 lm-eval/loglikelihood baseline | No, diagnostic only |
| MC 진단 | `open_telco_*_mcgen` | MC scoring sensitivity 분석 | Partial, diagnostic only |

bare `open_telco_otlite` / `open_telco_otfull`은 **실행 불가** —
run 스크립트가 fail-fast `exit 2`로 거부한다.

---

## 핵심 결론 — 격차의 원인

과거 "local 0.26 vs public 0.40 ≈ −13.8%p"로 보이던 격차의 거의 전부가
**scoring 방식(loglikelihood→generation) + 집계(sample-weighted→unweighted)**
차이로 설명된다.

`_gsma` profile 기준 sanity anchor:
gemma-3-4b-it ot-lite_gsma `0.3992` ≈ ot-full_gsma `0.3926` ≈ public `0.397`.

남은 격차의 귀인은 미확정이며 단일 원인으로 단정하지 않는다. 가장 큰
미정렬 축은 **MC 4종 engine** — 자유 single-letter generation vs 공식
제약 디코딩(지배적 격차 동인). 상세 분해는 [docs/03-gsma-alignment-and-caveats.md](03-gsma-alignment-and-caveats.md) 참조.

---

## 한계 요약

- 공식 GSMA stack(Inspect AI 기반) 완전 재현이 아님. engine·stack·집계 방식이 다르다.
- MC 4종은 자유 generation engine으로 공식 제약 디코딩과 미정렬(지배적 격차 동인).
- telelogs / 3gpp는 `\boxed{}` / WG token 미출력 시 soft scorer가 INCORRECT 처리 → 일부 모델 저점수는 형식-emission artifact(지식 격차 아님).
- reasoning 모델(R1-Distill 등)의 MC collapse는 engine 비호환 artifact이며 능력치가 아니다.
- license: 외부 배포 전 별도 결정 필요.

---

## 문서 map

| 문서 | 용도 |
|---|---|
| `docs/00-overview.md` | **이 문서** — 저장소 정체성·목적·profile·결론·한계 |
| `docs/01-quickstart.md` | 5분 시작 가이드 — 설치, smoke, bounded/full run, 비교 |
| `docs/02-profiles-and-scoring.md` | profile 상세, scoring contract, YAML 구조 |
| `docs/03-gsma-alignment-and-caveats.md` | public 비교 caveat, 격차 분해, MC engine 미정렬 |
| `docs/04-final-results.md` | 최종 평가 결과 수치 (모델별 unweighted task mean) |
| `docs/05-operations-and-troubleshooting.md` | 운영 변수, 대형 모델 설정, 알려진 장애 |
| `docs/06-inl-handoff.md` | INL 인수자 가이드 — 30분 acceptance test, 체크리스트 |
| `docs/07-release-notes.md` | PR #1~#6 변경 이력 |
| `docs/08-results-manifest.md` | 전달 산출물 위치·공유 안전 여부 |
| `docs/presentation-prompt-ko.md` | 발표용 프롬프트 (한국어) |
| `docs/archive/` | 구 문서 보관 |
