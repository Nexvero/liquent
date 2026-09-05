# LQ-1976 Shared joint engine API UTC validator

- One helper validates every outer UTC clock result.
- It returns only exact UTC-aware datetime values.
- Raw clock output never reaches decision logic.
- Accept and accepted audit use dedicated readers.
- Both readers share identical validation semantics.
- Existing clock sources remain time authorities.
- No new clock port is introduced.
