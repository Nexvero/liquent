# LQ-1785 Joint engine API terminal inventory equality

- Terminal inventory must equal the result registry tuple.
- Equality includes canonical order and tuple cardinality.
- Every acceptance and marker identity must remain equal.
- Every complete marker state must remain equal.
- Addition, removal, replacement, or mutation is rejected.
- No subset or run-only comparison is sufficient.
- Failure remains detail-free.
