.PHONY: smoke delivery-check test

smoke:
	bash scripts/smoke_test.sh

# Unit tests (pytest); uses the repo .venv so it runs without prior activation.
test:
	.venv/bin/python -m pytest -q tests/

# INL delivery readiness gate: tree-clean + bash -n + smoke + pytest + stale-wording
# + secret scan + large-tracked-file guard. GPU not required.
delivery-check:
	bash scripts/delivery_check.sh
