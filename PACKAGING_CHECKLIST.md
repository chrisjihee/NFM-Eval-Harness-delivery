# Packaging Checklist

Most checks below are automated by `make delivery-check`.

Before handoff:

- `git status --short` is clean.
- `bash -n run_open_telco_otlite.sh run_open_telco_otfull.sh setup-pre.sh setup-main.sh setup-post.sh` passes.
- `make smoke` passes.
- `pytest -q` passes.
- `make delivery-check` passes.
- No model weights are tracked.
- No Hugging Face cache is tracked.
- No raw sample dumps are tracked.
- No secrets or tokens are tracked.
- No tracked file exceeds 50 MB.
- `results/final/` contains only curated final evidence (60 result JSON + 20 `_aggregate.json`).
- README documents the start path, default `*_gsma` profile, and results location.
- Release tag command is documented (see `docs/07-release-notes.md` / `DELIVERY_PACKAGE.md`)
  but is NOT pushed by automation — the repository owner runs it manually.

LICENSE is TBD (owner decision); usage scope is documented in `USAGE_SCOPE.md`.
