# LQ-2086 Joint engine API accept single anchor preflight

- Accept checks exact anchor before initial UTC.
- It checks exact anchor before monotonic time.
- It checks exact anchor before root resolution.
- Double-slash input cannot reach mutation.
- Valid single-anchor input retains sequencing.
- Completion and failure gates remain unchanged.
- Signature remains unchanged.
