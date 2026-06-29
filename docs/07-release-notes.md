# 07 릴리스 노트

## v0.1.1 — 설치/런타임 정리 (2026-06-29)

### Changed

- **lm_eval 설치 방식**: git clone 후 editable(`-e --no-deps`) 설치 + 보조 6종 수동
  설치에서, PyPI 버전 고정 설치 `uv pip install "lm_eval[hf,vllm]==0.4.12"`로 전환했다.
  `[hf,vllm]` extra가 hf·vllm 백엔드와 lm_eval 보조 의존성을 함께 설치한다.
  lm-evaluation-harness git clone은 더 이상 수행하지 않는다(redundant). gsma-evals
  clone은 선택적 참조 전용으로 유지한다(런타임 의존성 아님 — scorer는 utils.py에 미러링).
- **기본 backend = vLLM**: `run_open_telco_*.sh`의 기본 backend를 `hf` → `vllm`로
  변경하고, vLLM 기본값으로 `MAX_MODEL_LEN=8192`·`GPU_MEMORY_UTILIZATION=0.9`를 적용했다.
  HF backend는 긴 생성형 입력을 left-truncation 하여 telelogs 등 생성형 task가 0점으로
  collapse할 수 있으므로(예: gemma-3-4b-it ot-lite_gsma에서 HF telelogs 0.0 vs vLLM 0.12)
  경량/대체 경로(`BACKEND=hf`)로 남긴다.

> 참고: `results/final/`의 수치는 동일 release(0.4.12) 계열 vLLM 측정값이며, PyPI
> 0.4.12 재실행 결과는 run-to-run 변동 범위 내에서 일치한다(수치: `docs/04-final-results.md`).

---

## v0.1-inl-delivery — slim 전달 저장소 초판 (2026-06-28)

이 저장소(`NFM-Eval-Harness-delivery`)는 EleutherAI lm-evaluation-harness 기반  
GSMA Open Telco 평가 하네스의 slim 문서 중심 전달본이다.  
원본 engineering-source 저장소(`NFM-Eval-Harness`)의  
전체 커밋·실험 이력은 원본에 보존되며, 이 저장소는 slim handoff 공개본이다. 정확한 engineering HEAD는 인수 시점의 원본 repo를 확인한다.

수치/결과 상세는 `docs/04-final-results.md` 참조. 본 노트는 수치를 재기재하지 않는다.

---

### Added

- **slim 문서 체계** (`docs/00`–`08`): 개요·퀵스타트·프로파일·정렬 분석·최종 결과·운영·INL 핸드오프·릴리스 노트·결과 매니페스트.
- **스크립트 5종**: `run_open_telco_otlite.sh`, `run_open_telco_otfull.sh`, `setup-pre.sh`, `setup-main.sh`, `setup-post.sh`, `scripts/aggregate_repeats.py`.
- **테스트 3종**: `tests/` 아래 parser·smoke·결과 정합성 검증.
- **results/final/** 디렉터리 구조: 10개 후보 모델 × `{otlite,otfull}-gsma` × run{1,2,3}/ 폴더 + `_aggregate.json`.  
  fresh rerun(3회 반복, mean±spread) **완료(2026-06-29)** — 60 result JSON + 20 `_aggregate.json`, 0 실패. 수치는 `docs/04-final-results.md`.

### Changed

- **루트 클러터 제거**: engineering-source의 `PLAN.md`, `HANDOFF.md`, `EXPERIMENTS.md`, `PROGRESS.md`, `REPRODUCTION_NOTES.md`, `GSMA_SCORING_CONTRACT.md`, `PACKAGING_CHECKLIST.md`, `INL_HANDOFF.md`, `chat/`, `lm-eval-ls-task` 등 내부 개발 아티팩트 미포함.
- **기본 task 프로파일**: `open_telco_otlite_gsma` / `open_telco_otfull_gsma`가 기본·권장 경로. run 스크립트가 `TASKS` 미지정 시 자동 선택.
- **legacy 오프-기본 경로**: `*_lm_eval_baseline`(loglikelihood 기반)은 diagnostic 목적으로만 보존되며 기본 실행 경로에 포함되지 않는다. bare `open_telco_otlite`/`open_telco_otfull`은 실행 불가(run 스크립트 `exit 2`).

### Validated

- `make smoke` — task YAML 로딩 및 의존성 검증 통과.
- `pytest tests/` — parser·smoke·정합성 테스트 통과.
- `make delivery-check` — 금지 문구·tracked 파일 크기(50MB 이하) 게이트 통과.
- from-scratch setup(`setup-pre.sh` → `setup-main.sh` → `setup-post.sh` → `make smoke`) 흐름 검증.

### Known Limitations

- **공식 GSMA stack 완전 재현 아님**: 공식은 Inspect AI 기반, 이 하네스는 lm-eval 기반. 동일 점수 재현은 목표가 아니다.
- **MC engine 미정렬**: MC 4종은 자유 single-letter `generate_until` 방식(`max_gen_toks:8`)이며, 공식의 제약 디코딩(`multiple_choice(cot=False)`)과 다르다. 이 차이가 가장 큰 점수 격차 요인이다.
- **reasoning/harmony 모델 비호환**: enable_thinking 미해제·단답 출력 미조정 상태의 reasoning 모델은 MC engine collapse가 artifact이므로 비교에서 제외한다.
- **teletables**: 기본 `_gsma` profile은 question+choices를 제공해 평가하므로 GSMA parity이며 저평가가 아니다. legacy/superset 표 원본이 필요한 경우에만 `TELETABLES_ROOT`를 설정한다(기본 전달 경로엔 불필요).

### Not Included

- model weights / HF cache / per-sample dump(`.jsonl`) / raw log — 전부 비추적·미포함.
- engineering-source의 실험 이력(`chat/`, `lm-eval-ls-task`, `results/smoke-*`, `results/conf-*`).
- 멀티모달·LMM·LAM, 동적 제어, Planning(Intent→Recipe), RAG-grounded QA, Korean Telco QA(2차 과제 범위).

### Reproducibility

- 환경 핀: Python 3.12.13, torch 2.11.0+cu128, transformers 5.12.1, vllm 0.23.0.
- lm_eval: PyPI release `0.4.12` 고정 — `setup-post.sh`의 `uv pip install "lm_eval[hf,vllm]==0.4.12"`. (과거 engineering 트랙은 git clone + SHA `97a5e2c7` = `v0.4.12`+12 commits를 핀했으나, 전달본은 재현 단순화를 위해 PyPI release를 사용한다.)
- gsma-evals: `gsma-labs/evals` — (선택) `setup-post.sh`가 참조용 clone. 런타임 의존성 아님(scorer는 utils.py에 미러링). 임의 수정 금지.
- VM 운영 레시피(NCCL loopback + HF offline cache)는 `docs/05-operations-and-troubleshooting.md` 참조.

---

## License Posture

이 저장소의 라이선스는 현재 **TBD**이다(원본 engineering-source 저장소와 동일하게 명시 라이선스 없음; INL 내부 사용 기준).  
별도 라이선스 결정 전까지 재배포 라이선스를 부여하지 않는다.

포함된 third-party 컴포넌트(`lm-evaluation-harness`, `gsma-evals`)는 각자 고유 라이선스를 따른다.  
사용 전 해당 저장소의 라이선스 조건을 확인한다. 사용 범위(범위 밖: 멀티모달/LMM/LAM, Planning, RAG, 한국어 QA 등 2차 과제)는 `docs/00-overview.md` 및 `README.md`의 범위 절을 참조한다.

---

## Release tag preparation

저장소 소유자는 아래 명령으로 handoff 태그를 생성할 수 있다(자동 실행하지 않음):

```bash
git tag -a v0.1-inl-handoff-2026-06-29 -m "INL handoff package"
git push origin v0.1-inl-handoff-2026-06-29
```

Do not run this automatically — 소유자가 최종 확인 후 직접 실행한다.
