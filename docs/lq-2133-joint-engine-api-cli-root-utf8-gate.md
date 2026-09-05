# LQ-2133 Joint engine API CLI root UTF-8 gate

- Root text must encode without Unicode error.
- Surrogate-only text is not accepted.
- Encoding occurs exactly once for total size.
- Valid Unicode spelling remains unchanged.
- No replacement character is introduced.
- No alternate encoding is attempted.
- Encoding failure uses unavailable rejection.
