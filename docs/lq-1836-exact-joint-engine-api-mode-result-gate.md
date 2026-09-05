# LQ-1836 Exact joint engine API mode result gate

- Requested mode determines one expected result class.
- Runtime result type must equal that class exactly.
- Generic branch recognition cannot override mode intent.
- A valid result for another mode still fails closed.
- Result contents are checked only after mode binding.
- Existing result validators remain independently active.
- No caller-supplied role or allow flag is introduced.
