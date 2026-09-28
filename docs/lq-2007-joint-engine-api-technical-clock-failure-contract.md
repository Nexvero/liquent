# LQ-2007 Joint engine API technical clock failure contract

- Technical clock failure is detail-free unavailability.
- It is distinct from a malformed returned value internally.
- Callers receive the same established failure type.
- No provider name or stage is disclosed.
- No retry is introduced.
- No alternate time source is consulted.
- No new exception is named.
