# LQ-1916 Shared joint engine API acceptance observation reader

- One helper composes marker observation and type validation.
- It returns only exact acceptance observations.
- Raw observer output never reaches operation logic.
- Run identity and root identity are mandatory.
- No fallback unbound marker read is available.
- Existing observer remains marker evidence authority.
- No new port or persistence model is introduced.
