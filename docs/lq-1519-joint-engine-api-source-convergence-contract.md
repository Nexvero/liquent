# LQ-1519 Joint engine API source convergence contract

- One source observation requires two matching child-content passes.
- Both passes use descriptor-relative no-follow reads.
- Content mismatch fails before a snapshot becomes evidence.
- Stable metadata is required independently in each pass.
- Root layout and identity checks remain mandatory.
- Failure remains detail-free and fail-closed.
- No retry or majority decision is introduced.
