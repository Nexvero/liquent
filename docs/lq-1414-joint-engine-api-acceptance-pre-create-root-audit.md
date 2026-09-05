# LQ-1414 Joint engine API acceptance pre-create root audit

- A root detached before creation cannot receive an orphan marker.
- A rebound visible root cannot redirect marker creation.
- Pre-create validation is separate from final publication validation.
- Both checks use the same no-follow visible-root identity policy.
- Existing exclusive marker creation semantics remain unchanged.
- Focused pre-create and acceptance regression evidence passes.
- External staging evidence remains a separate readiness condition.
