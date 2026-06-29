# Final Audit Delta

INL 전달본(delivery repo) 최종 polish를 위한 read-only audit 결과. (PASS 8, 2026-06-29)

## 1. Audit scope
- engineering source repo: `~/code/NFM-Eval-Harness` (provenance, 수정 금지)
- handoff delivery repo: `~/code/NFM-Eval-Harness-delivery` (정본, 최소 침습 수정 대상)

## 2. Current repository status
- engineering HEAD: `fd2412a` ("Save chat only local" — 소유자 외부 커밋, 본 작업과 무관, 무수정 보존)
- delivery HEAD: `a0f49c6` (origin/master 동기화, working tree clean)
- git status: 양쪽 모두 clean(0건)
- tracked result footprint: `results/final/` = 60 result JSON + 20 `_aggregate.json` (최대 파일 ~36KB, >50MB 0건)

## 3. Keep / archive / remove table

| path | repo | category | keep | archive | remove | reason | action_needed |
|---|---|---|:--:|:--:|:--:|---|:--:|
| `README.md` | delivery | doc | ✅ | | | 진입점 — results/final 위치 보강 필요 | yes |
| `docs/00–08*.md` | delivery | doc | ✅ | | | 정본 문서 셋 | no |
| `docs/presentation-prompt-ko.md` | delivery | doc | ✅ | | | 발표 프롬프트(실제 결과 포함) | no |
| `docs/archive/README.md` | delivery | archive | ✅ | | | 연혁 요약 | no |
| `INL_HANDOFF.md` / `DELIVERY_PACKAGE.md` / `RESULTS_MANIFEST.md` / `PACKAGING_CHECKLIST.md` | delivery | doc(root) | | | | **부재 → thin stub 신규 생성** | yes |
| `USAGE_SCOPE.md` | delivery | doc(root) | | | | **부재 → 신규 생성(license TBD)** | yes |
| `LICENSE` | delivery | — | | | | 부재 — owner 결정 전까지 추가 금지 | no(owner) |
| `docs/archive/engineering-history-index.md` | delivery | archive | | | | **부재 → 신규 생성** | yes |
| `docs/archive/final-audit-delta.md` | delivery | archive | ✅ | | | 본 audit 산출물 | (this) |
| `scripts/{compare_gsma_leaderboard,aggregate_repeats}.py` | delivery | script | ✅ | | | 비교·집계 핵심 | no |
| `scripts/{smoke_test,delivery_check}.sh`, `check_tracked_file_sizes.py` | delivery | script | ✅ | | | 검증 게이트 | no |
| `tests/test_{mc_gen,parsers_characterization,gsma_parsers}.py` | delivery | test | ✅ | | | 최소 회귀(MC추출·parser·scorer) | no |
| `results/final/**` | delivery | result | ✅ | | | fresh rerun 정본 증거 | no |
| `check_vllm_runtime.py` | delivery | script | ✅ | | | setup-main이 참조 | no |
| `open_telco_lm_eval/tasks/**` | delivery | code | ✅ | | | task pack 전체(group/importlib) | no |
| raw chat/log/sample dump/cache/weights | delivery | — | | | n/a | delivery에 부재(섞이지 않음 ✓) | no |
| engineering repo 전체 | engineering | provenance | ✅(보존) | | | 수정 금지 | no |

## 4. Issues found
- **blocker**: 없음. (delivery-check PASS, smoke/pytest/link/secret/size 전부 통과, 원본 무변경.)
- **should-fix (delivery only)**:
  1. root alias stub 4종 부재 → thin stub 생성.
  2. `USAGE_SCOPE.md` 부재 → 생성(license TBD, 과도주장 금지 문구 포함).
  3. `docs/archive/engineering-history-index.md` 부재 → 생성.
  4. `README.md`에 결과 위치(`results/final/`) 미언급 + "recommended handoff entry point" 강조 약함 → 보강.
  5. TeleTables "degraded/metadata-only" 표현(docs/07:40, docs/05:95)이 `_gsma`=question+choices parity와 혼동 소지 → `_gsma`에선 parity, `TELETABLES_ROOT`는 legacy/superset 한정임을 명확화.
- **optional**:
  - `delivery_check.sh`에 `results/final/**` 존재 여부 검사 1줄 추가 가능(현재 미포함). 최소 침습 원칙상 보류 가능.
  - bare name(`open_telco_otlite/otfull`)은 fail-fast/historical/예시 맥락에만 등장(권장처럼 표기된 곳 없음 ✓).
  - "공식 완전 재현" 매칭은 전부 부정 caveat(과도주장 아님 ✓).

## 5. Planned minimal changes (delivery repo only)
- root: `INL_HANDOFF.md`, `DELIVERY_PACKAGE.md`, `RESULTS_MANIFEST.md`, `PACKAGING_CHECKLIST.md`, `USAGE_SCOPE.md` 생성(thin stub / scope note).
- docs/archive: `engineering-history-index.md`, `final-audit-delta.md`(본 파일) 생성.
- `README.md`: handoff 정본 문구 보강 + `results/final/` 위치 + acceptance test 블록.
- `docs/07-release-notes.md`: TeleTables `_gsma` parity 명확화 + release tag 명령(미실행) 문서화.
- `docs/05-operations-and-troubleshooting.md`: `TELETABLES_ROOT` 설명을 legacy/superset 한정으로 명확화.
- **engineering repo: 무변경 원칙 유지.**

## 6. Validation plan
- `bash -n` 전 스크립트, `make smoke`, `pytest -q`, `make delivery-check`, `LIMIT=1` 기본 smoke, `compare --help`.
- 가능 시 vLLM `LIMIT=1` smoke(GPU 가용 시), 불가 시 사유 기록.
- 변경 후 본 문서 하단에 "검증 결과" 섹션 갱신.

---

## 7. 검증 결과 (Phase C)

### Modified / added files (delivery repo, commit `fa6e465`)
- 신규(root): `INL_HANDOFF.md`, `DELIVERY_PACKAGE.md`, `RESULTS_MANIFEST.md`, `PACKAGING_CHECKLIST.md`, `USAGE_SCOPE.md`
- 신규(archive): `docs/archive/engineering-history-index.md`, `docs/archive/final-audit-delta.md`
- 편집: `README.md`(정본 문구·results/final·30분 acceptance test·USAGE_SCOPE 링크),
  `docs/07-release-notes.md`(rerun 완료·TeleTables parity·release tag),
  `docs/05-operations-and-troubleshooting.md`(TELETABLES_ROOT legacy 한정),
  `docs/presentation-prompt-ko.md`(TeleTables question+choices parity)

### Validation summary
- `bash -n` (run/setup 5종): PASS
- `make smoke`: PASS
- `pytest -q`: 73 passed
- `make delivery-check`: PASS (tree-clean / bash -n / smoke / pytest / stale / secret / 50MB / docs-link 전부)
- `LIMIT=1` 기본(hf) smoke: PASS (exit 0; acc=0.2857 — 1-sample이라 수치 무의미, 파이프라인 동작 확인)
- `LIMIT=1` vLLM smoke(MAX_MODEL_LEN=8192, enforce_eager): PASS (exit 0)
- `compare_gsma_leaderboard.py --help`: PASS

### Skipped validation
- 없음. (GPU 가용으로 hf·vLLM smoke 모두 수행.)

### Remaining optional items (결정 대기 — 누락 아님)
- LICENSE: owner 결정 전까지 파일 미추가(`USAGE_SCOPE.md`에 TBD 명시).
- release tag: 명령만 문서화, owner가 직접 실행.
- (선택) `delivery_check.sh`에 `results/final/**` 존재 검사 1줄 추가 — 최소 침습 원칙상 미적용.

### Engineering repo
- 무변경 보존(HEAD `fd2412a`, 외부 소유자 커밋, 본 작업과 무관).
