# LQ-1813 Joint engine API accepted evidence shape evidence

- Tests reject null verifier evidence.
- Tests reject empty and one-value tuples.
- Tests reject oversized tuples and list containers.
- Tests reject wrong values in an exact tuple.
- Tests prove rejection precedes success callback.
- Detail-free boundary text remains stable.
- All focused warnings are treated as errors.
