# LQ-1575 Joint engine API intended acceptance state change contract

- Successful accept intentionally creates one marker entry.
- That write legitimately changes acceptance-directory state.
- Only accept may permit this state difference at final validation.
- Operation-root and source states must still remain exact.
- Acceptance path and identity must remain exact.
- Audit never receives this exception.
- Boolean opt-in is internal and exact.
