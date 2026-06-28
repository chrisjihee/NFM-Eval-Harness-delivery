.PHONY: smoke delivery-check

smoke:
	bash scripts/smoke_test.sh

# INL delivery readiness gate: tree-clean + bash -n + smoke + pytest + stale-wording
# + secret scan + large-tracked-file guard. GPU not required.
delivery-check:
	bash scripts/delivery_check.sh
