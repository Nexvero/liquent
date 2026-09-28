# LQ-1372 Joint engine API operation mode finalization

- Accept mode supplies source and acceptance paths to one-shot verification.
- Registry audit supplies only the bound acceptance path to inspection.
- Accepted-source audit supplies both bound paths to current verification.
- Shared wrapper finalization follows each internal operation uniformly.
- Final re-resolution compares root and both children against one baseline.
- A final mismatch converts the complete mode call to closed rejection.
- Existing parser and mode selection remain unchanged.
