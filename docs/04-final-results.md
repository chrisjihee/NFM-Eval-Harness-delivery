# 04 — Final Results (fresh rerun, mean ± spread)

이 표의 점수는 **이 전달 저장소(`NFM-Eval-Harness-delivery`)의 run 스크립트로 새로 수행한**
`open_telco_otlite_gsma` / `open_telco_otfull_gsma` 결과다(2026-06-29, vLLM, `MAX_MODEL_LEN=8192`).
각 (모델 × profile)을 **3회 동일 실행**하고 `scripts/aggregate_repeats.py`로
**per-run unweighted 7-task mean의 평균 ± 표본표준편차(n−1)**를 보고한다(전 모델 `n=3`, 실패 0).
비교 기준은 항상 **7-task unweighted task mean** vs public **unweighted**다.

- 결과 경로: `results/final/{otlite,otfull}-gsma-<label>/run{1,2,3}/.../results_*.json` + 동일 디렉터리 `_aggregate.json`.
- 산출물 위치·공유 안전성은 [08-results-manifest.md](08-results-manifest.md), 방법론 caveat은 [03-gsma-alignment-and-caveats.md](03-gsma-alignment-and-caveats.md).

## 핵심 요약

- **public leaderboard 비교는 동일 split인 ot-full_gsma 기준**이다(ot-lite는 다른 split이므로 public과 직접 비교하지 않는다).
- **leaderboard 7개 모델 중 gemma3-12b를 제외한 6개의 |Δ(ot-full−public)| ≤ 0.021(평균 0.009)** 로 public에 근접했다(공식 재현은 아님 — 방법론 차이는 §caveat 참조).
  reference anchor `gemma-3-4b-it` = ot-full **0.3887** vs public **0.397**(Δ −0.008).
- **gemma3-12b만 Δ −0.037**로 큰데, 이는 telemath/telelogs에서 `\boxed{}`/라벨 emission이 취약해(긴 생성으로 이어짐) 생성형 점수가 낮기 때문이다(능력 저하가 아니라 emission 특성; [03](03-gsma-alignment-and-caveats.md) 참조).
- **이것은 공식 GSMA stack(Inspect AI) 재현이 아니다.** 특히 MC 4종은 자유 generation engine으로 공식 제약 디코딩과 **미정렬**이다 — delta가 작아도 "공식 재현"으로 해석하지 않는다.

## 결과 표 (3회 평균 ± 표준편차, n=3)

| model_id | LB | ot-lite_gsma | ot-full_gsma | public | Δ(ot-full−pub) | strongest | weakest | 비고 |
|---|:--:|---|---|---:|---:|---|---|---|
| `google/gemma-3-4b-it` | yes | 0.3956±0.0000 | 0.3887±0.0011 | 0.3970 | −0.0083 | srsranbench | telemath | reference anchor(≈public) |
| `Qwen/Qwen2.5-7B-Instruct` | yes | 0.4558±0.0084 | 0.4479±0.0026 | 0.4579 | −0.0101 | srsranbench | telelogs | — |
| `tiiuae/Falcon3-10B-Instruct` | yes | 0.4714±0.0016 | 0.4620±0.0020 | 0.4588 | +0.0032 | srsranbench | telelogs | — |
| `google/gemma-3-12b-it` | yes | 0.4357±0.0062 | 0.4267±0.0006 | 0.4638 | −0.0371 | srsranbench | telemath | MAX_MODEL_LEN=8192; telemath/telelogs emission 취약 |
| `microsoft/phi-4` | yes | 0.5279±0.0000 | 0.4971±0.0005 | 0.5045 | −0.0075 | srsranbench | telelogs | GMU=0.9 |
| `mistralai/Mistral-Small-24B-Instruct-2501` | yes | 0.5078±0.0022 | 0.4954±0.0021 | 0.5163 | −0.0208 | oranbench | telelogs | tp=2; tokenizer_mode=mistral |
| `Qwen/Qwen2.5-32B-Instruct` | yes | 0.5068±0.0067 | 0.5048±0.0014 | 0.5067 | −0.0019 | srsranbench | telelogs | tp=2 |
| `Qwen/Qwen3-4B` | no | 0.4530±0.0061 | 0.4368±0.0027 | — | — | srsranbench | telelogs | internal ref; enable_thinking=False |
| `Qwen/Qwen3-14B` | no | 0.4644±0.0000 | 0.4623±0.0008 | — | — | srsranbench | telelogs | internal ref; enable_thinking=False |
| `Qwen/Qwen3-30B-A3B-Instruct-2507-FP8` | no | 0.4707±0.0010 | 0.4629±0.0022 | — | — | srsranbench | telelogs | internal ref; tp=2; FP8(PASS5 검증) |

- `±0.0000`은 greedy 디코딩으로 3회가 동일(deterministic)함을 정직히 표기한 것이다(spread 조작 아님).
- `public`/`Δ`는 leaderboard row가 있는 모델만 채운다(`GSMA/leaderboard`의 7-task unweighted mean). `LB=no`는 public 비교 없이 internal 상대비교만 한다.
- strongest/weakest는 해당 모델 **ot-full per-task**의 최고/최저 task다. 모든 모델에서 통신 MC(srsranbench/oranbench)가 강하고 생성형(telelogs/telemath)이 약한 공통 패턴이 보인다.

## leaderboard 7개 모델 Δ(ot-full − public)

| model | Δ |
|---|---:|
| gemma3-4b | −0.0083 |
| qwen2.5-7b | −0.0101 |
| falcon3-10b | +0.0032 |
| gemma3-12b | **−0.0371** |
| phi-4 | −0.0075 |
| mistral-small-24b | −0.0208 |
| qwen2.5-32b | −0.0019 |

**비-gemma3-12b 6개: |Δ| 최대 0.021, 평균 0.009.** delta 부호가 +/−로 엇갈려(falcon +0.003) 억지 정렬이 아님을 보인다.

## Excluded / substituted models and reasons

| model | reason |
|---|---|
| openai/gpt-oss-20b | harmony special-format 강제 → 단답 MC collapse(artifact, 능력 아님) |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-14B | always-reasoning, `enable_thinking=False` 무시 → MC truncate collapse(artifact) |
| google/gemma-4-E4B | 토크나이저 비호환 |
| Qwen3.6-27B-FP8 | 다운로드 실패(※ rerun #10 `Qwen3-30B-A3B-Instruct-2507-FP8`와 다른 모델) |

- 이번 rerun에서 **모델 대체는 없었다**: #10 `Qwen/Qwen3-30B-A3B-Instruct-2507-FP8`이 정상 로딩·완료되어 Qwen3-8B 대체(fallback)는 사용되지 않았다.
- 제외 모델의 낮은/붕괴 점수는 **engine 비호환에 따른 artifact**이며 모델 능력 평가가 아니다(reasoning/harmony 계열은 단답 MC engine과 구조적으로 비호환, [03](03-gsma-alignment-and-caveats.md)).

## 재현 명령(단일 모델)

```bash
# ot-lite_gsma 3회 (예: gemma-3-4b-it)
for r in 1 2 3; do CONFIRM_FULL_RUN=1 BACKEND=vllm VLLM_VISIBLE_DEVICES=0 \
  MAX_MODEL_LEN=8192 GPU_MEMORY_UTILIZATION=0.9 EXTRA_MODEL_ARGS=enforce_eager=True \
  MODEL_NAME=google/gemma-3-4b-it OUTPUT_PATH=results/final/otlite-gsma-gemma3-4b/run$r \
  ./run_open_telco_otlite.sh; done
python scripts/aggregate_repeats.py results/final/otlite-gsma-gemma3-4b/run{1,2,3} \
  --label otlite-gsma-gemma3-4b --out-json results/final/otlite-gsma-gemma3-4b/_aggregate.json
```

대형 모델(24~33B)은 `TENSOR_PARALLEL_SIZE=2 VLLM_VISIBLE_DEVICES=0,1`, Mistral은
`EXTRA_MODEL_ARGS=enforce_eager=True,tokenizer_mode=mistral`, Qwen3 계열은
`...,enable_thinking=False`를 사용한다([05-operations-and-troubleshooting.md](05-operations-and-troubleshooting.md)).
