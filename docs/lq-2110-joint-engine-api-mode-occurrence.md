# LQ-2110 Joint engine API mode occurrence

- Mode option is required once.
- A second mode never replaces the first.
- An identical second mode is still invalid.
- No last-value-wins behavior exists.
- Duplicate rejection precedes mode binding.
- No operation reaches dispatch after duplication.
- No fallback mode exists.
