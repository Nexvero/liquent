# LQ-2134 Joint engine API CLI root control character gate

- NUL remains rejected.
- Tab and line controls are rejected.
- Every C0 control character is rejected.
- DEL is rejected.
- Printable Unicode remains eligible.
- No control character reaches Path construction.
- No escaping fallback exists.
