# LQ-1808 Exact joint engine API accepted evidence tuple

- Evidence container type must be exactly tuple.
- Tuple cardinality must be exactly two.
- Position one carries retained source observation.
- Position two carries retained acceptance observation.
- No coercion or normalization is performed.
- Caller-shaped iterable compatibility is intentionally absent.
- Existing verifier remains the evidence authority.
