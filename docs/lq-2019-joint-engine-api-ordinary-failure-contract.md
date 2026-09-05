# LQ-2019 Joint engine API ordinary failure contract

- Ordinary implementation failure means technical unavailability.
- It does not imply neutral absence.
- It does not imply policy rejection.
- Callers receive no dependency or stage detail.
- No automatic retry follows failure.
- Durable state follows completed inner writes.
- No new exception is named.
