# LQ-2123 Joint engine API raw to native root handoff

- Canonical raw text constructs one native Path.
- Exact native Path validation follows conversion.
- Namespace receives only validated native Path.
- Dispatcher receives the same Path identity.
- Direct preflight independently repeats native checks.
- No raw text reaches operation logic.
- No path evidence is returned.
