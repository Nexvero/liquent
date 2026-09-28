# LQ-1947 Joint engine API root completion failure contract

- Foreign validator return uses unavailable failure.
- No truthy or falsey value becomes implicit success.
- Validator return details never enter failure text.
- Completion failure may override hidden inner failure detail.
- Durable operation state remains untouched.
- CLI status mapping remains unchanged.
- No new exception name is introduced.
