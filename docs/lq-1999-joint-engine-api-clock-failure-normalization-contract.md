# LQ-1999 Joint engine API clock failure normalization contract

- Every outer clock provider crosses one failure boundary.
- Ordinary technical provider failures become unavailable.
- Existing unavailable failures pass through unchanged.
- System exits and interrupts are not swallowed.
- Provider details remain private.
- Validation and failure normalization compose.
- Public command behavior remains unchanged.
