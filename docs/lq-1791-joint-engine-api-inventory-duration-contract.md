# LQ-1791 Joint engine API inventory duration contract

- Terminal inventory verification precedes the final clock read.
- Its execution remains inside the thirty-second budget.
- A slow or unstable read cannot escape timing policy.
- Monotonic rollback still fails closed.
- Wall-clock freshness remains source-specific.
- No additional clock source or budget is introduced.
- Existing timing failure remains detail-free.
