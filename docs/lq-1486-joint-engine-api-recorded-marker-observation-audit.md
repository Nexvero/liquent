# LQ-1486 Joint engine API recorded marker observation audit

- LQ-1483 through LQ-1485 close write-time marker identity capture.
- Durable write evidence now identifies its concrete marker generation.
- Path and content alone are no longer the complete write result.
- Registry-root binding remains independently mandatory.
- Existing fail-closed failure windows are preserved.
- No rollback, retry, or cleanup policy was expanded.
- Final generation comparison remains the next boundary.
