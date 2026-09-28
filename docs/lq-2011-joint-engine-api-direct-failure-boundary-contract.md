# LQ-2011 Joint engine API direct failure boundary contract

- Every direct operation crosses one outer failure boundary.
- Ordinary technical failures become unavailable.
- Existing unavailable failures pass through unchanged.
- System exits and interrupts are not swallowed.
- Failure details remain private.
- Root closure completes before normalization.
- Public command behavior remains unchanged.
