# LQ-1959 Joint engine API snapshot completion failure contract

- Foreign verifier return uses unavailable failure.
- No truthy or falsey value becomes implicit success.
- Verifier return details never enter failure text.
- Durable operation state remains untouched.
- Root final validation still closes operation.
- CLI status mapping remains unchanged.
- No new exception name is introduced.
