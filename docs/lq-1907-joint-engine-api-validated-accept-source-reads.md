# LQ-1907 Joint engine API validated accept source reads

- Accept operation captures source through shared reader.
- First success source recheck uses the same boundary.
- Post-freshness source recheck uses the same boundary.
- Terminal source recheck uses the same boundary.
- All four observations must remain exactly equal.
- Every read uses the same source-root identity.
- Mutation and timing semantics remain unchanged.
