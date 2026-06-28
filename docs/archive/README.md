# archive — 개발 연혁 요약 및 third-party 안내

이 디렉터리는 원본 engineering-source 저장소(`NFM-Eval-Harness`)의 개발 이력을  
slim 전달본 맥락에서 간략히 요약한다. 원본의 전체 PR·commit·실험 이력은  
engineering-source 저장소에 보존된다(이 slim 저장소에 복제하지 않는다).

---

## 개발 연혁 요약

| PR | 내용 |
|---|---|
| #1 | lm-eval baseline 초기 구현 — TeleQnA·3GPP·ORANBench·srsRANBench·TeleMath·TeleLogs 7-task YAML + utils.py |
| #2 | GSMA scoring contract 정렬 — `*_gsma` / `*_mcgen` profile 추가, 집계방식 정정(sample-weighted → unweighted task mean), gemma3-4b reference run |
| #3 | task 이름 정리 — 기본 경로를 `*_gsma`로 정착, bare name fail-fast, legacy를 `*_lm_eval_baseline`으로 rename |
| #4 | 전달 6종 모델 평가 — gemma/qwen/mistral 계열 ot-lite_gsma screening, PASS4 delivery bundle |
| #5 | 확장 평가 — 11종 ot-lite + 14종 ot-full, VM 운영 레시피(NCCL loopback + HF offline), LB 비교 검증(비-gemma3 ±0.021 이내) |
| #6 | INL 패키징 — 전달 문서(`INL_HANDOFF`, `RESULTS_MANIFEST`, `PACKAGING_CHECKLIST`, `RELEASE_NOTES`) + `make delivery-check` 게이트 |

주요 이정표:

- **lm-eval baseline → GSMA contract 정렬**: MC 4종을 loglikelihood에서 generation-based scoring으로 전환(비-default `*_mcgen`) 후 공개 scorer 정렬 `*_gsma` 추가.
- **이름 정리**: bare task name을 fail-fast로 막고 `_gsma` / `_lm_eval_baseline` / `_mcgen` suffix 체계로 명확화.
- **다중 모델 검증**: 11~14종 후보 모델에 걸쳐 ot-lite 스크리닝 후 ot-full full-split 실행, leaderboard 수치 재현 확인.
- **slim 전달**: engineering-source를 그대로 전달하는 대신 문서 중심 slim 저장소로 분리·패키징.

---

## Third-party Vendor Note

이 하네스는 두 개의 third-party 저장소에 의존한다. 두 저장소 모두 `setup-post.sh`가 clone하며  
임의 수정 금지이다. 버전 변경 시 평가 재현성에 영향을 미치므로 반드시 검토 후 진행한다.

| 컴포넌트 | 출처 | 고정 버전 | 역할 |
|---|---|---|---|
| `lm-evaluation-harness` | EleutherAI/lm-evaluation-harness | SHA `97a5e2c7` | 평가 엔진 — task 실행·채점·집계 |
| `gsma-evals` | gsma-labs/evals | (setup-post.sh 지정 버전) | 공식 GSMA scorer 소스(telemath isclose / telelogs soft / 3gpp WG regex) |

`setup-post.sh` 외부에서 이 저장소들을 별도 수정하거나 다른 commit으로 교체하면  
`make smoke` 및 `pytest tests/`가 실패할 수 있다.
