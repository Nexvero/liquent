# LQ-2038 Joint engine API accept request preflight

- Accept validates root before initial UTC.
- It validates root before initial monotonic time.
- It validates root before descriptor work.
- Invalid input cannot reach mutation.
- Valid input retains existing sequencing.
- Completion and failure gates remain outermost.
- Signature remains unchanged.
