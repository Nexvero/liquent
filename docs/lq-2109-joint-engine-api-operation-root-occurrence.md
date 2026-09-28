# LQ-2109 Joint engine API operation root occurrence

- Operation-root option is required once.
- A second root never replaces the first.
- An identical second root is still invalid.
- No last-value-wins behavior exists.
- Duplicate rejection precedes root validation.
- No root reaches dispatch after duplication.
- No fallback root exists.
