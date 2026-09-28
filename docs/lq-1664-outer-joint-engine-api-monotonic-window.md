# LQ-1664 Outer joint engine API monotonic window

- One monotonic read precedes inner operation execution.
- One monotonic read follows success reobservations.
- Their difference bounds the complete decision path.
- Inner one-shot duration remains independently bounded.
- Exactly 30 seconds remains accepted.
- Negative or non-finite clocks fail at clock boundary.
- No caller duration is accepted.
