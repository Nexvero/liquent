# LQ-1467 Joint engine API bound readback contract

- Durable acceptance requires readback from the resolved registry.
- The final marker load must verify the original registry identity.
- A replacement after record cannot satisfy durable confirmation.
- Equal marker bytes do not substitute for registry continuity.
- Readback remains additional to file and directory synchronization.
- Failure stays detail-free and invalidates the acceptance decision.
- No cleanup or rollback policy is added by this slice.
