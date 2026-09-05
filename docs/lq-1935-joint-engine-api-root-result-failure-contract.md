# LQ-1935 Joint engine API root result failure contract

- Malformed resolver output uses unavailable failure.
- No attribute or dataclass error determines rejection.
- Resolver return details never enter failure text.
- Initial failure prevents all operation work.
- Post-operation failure preserves durable state.
- Final validation still closes every entered sandwich.
- No new exception name is introduced.
