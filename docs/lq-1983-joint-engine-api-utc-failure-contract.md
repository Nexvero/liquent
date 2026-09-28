# LQ-1983 Joint engine API UTC failure contract

- Malformed clock output uses unavailable failure.
- No datetime comparison error determines rejection.
- Clock return details never enter failure text.
- Initial failure prevents operation work.
- Late failure preserves durable state.
- Root final validation still closes entered operation.
- No new exception name is introduced.
