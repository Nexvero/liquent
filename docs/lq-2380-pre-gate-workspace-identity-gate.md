# LQ-2380 Pre-gate workspace-identity gate

- Immediately before every configured gate executes, the workspace is reopened
  without following links and compared with the run-bound identity.
- A previous phase cannot redirect or relax the workspace for a later phase.
- Failure stops the fixed phase sequence before another gate receives the path.
- No repair, mode restoration, or alternate workspace is attempted.
- Gate receipts cannot override this filesystem decision.
