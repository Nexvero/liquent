# LQ-1449 Joint engine API acceptance read identity evidence

- Exact descriptor identity permits load and registry inspection.
- Invalid tuple shapes and values are rejected for both operations.
- An identically copied replacement registry is rejected.
- Rejection occurs before its marker bytes can become evidence.
- Existing unbound read behavior remains regression-covered.
- Tests cover observable filesystem identity behavior only.
- Local evidence does not constitute deployment attestation.
