# LQ-1795 Joint engine API terminal registry audit contract

- Read-only registry audit ends with a terminal recheck.
- Acceptance values and marker observations are both rechecked.
- Both must equal the closed audit result exactly.
- The recheck occurs after the first duration decision.
- A final monotonic decision closes all terminal work.
- Divergence fails closed without detail.
- Public audit output remains unchanged.
