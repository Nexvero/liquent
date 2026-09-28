# LQ-1760 Canonical joint engine API result inventory ordering

- Result inventories use ascending canonical run-id order.
- Construction rejects every noncanonical permutation.
- Ordering is checked before a result crosses its handoff.
- No caller-selected ordering becomes trusted evidence.
- Empty and singleton inventories remain naturally canonical.
- Rejection uses the existing detail-free boundary failure.
- Persistent registry ordering remains unchanged.
