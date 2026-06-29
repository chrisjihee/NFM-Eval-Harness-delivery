# Delivery Package

This file is a thin entry point. The single source of truth lives under `docs/`.

Primary documents:
- `docs/00-overview.md`
- `docs/01-quickstart.md`
- `docs/02-profiles-and-scoring.md`
- `docs/03-gsma-alignment-and-caveats.md`
- `docs/04-final-results.md`
- `docs/05-operations-and-troubleshooting.md`
- `docs/06-inl-handoff.md`
- `docs/07-release-notes.md`
- `docs/08-results-manifest.md`

Final curated results are under `results/final/`.

Usage scope / license posture: `USAGE_SCOPE.md`.
Pre-handoff checklist: `PACKAGING_CHECKLIST.md`.

## Release tag preparation

The repository owner may create the handoff tag with:

```bash
git tag -a v0.1-inl-handoff-2026-06-29 -m "INL handoff package"
git push origin v0.1-inl-handoff-2026-06-29
```

Do not run this automatically.
