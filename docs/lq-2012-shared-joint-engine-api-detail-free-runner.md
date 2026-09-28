# LQ-2012 Shared joint engine API detail-free runner

- One private runner owns ordinary exception normalization.
- It invokes one supplied operation exactly once.
- Successful return values pass through unchanged.
- Existing unavailable instances preserve identity.
- Ordinary exceptions lose explicit cause detail.
- Base-level system control flow remains outside.
- No public port is added.
