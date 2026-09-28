# LQ-1991 Joint engine API three-stage accept monotonic

- Accept validates initial monotonic time.
- It validates final convergence time.
- It validates terminal closure time.
- Initial failure prevents operation work.
- Later failure preserves accepted durable state.
- All comparisons consume canonical values.
- Existing three-read ordering remains unchanged.
