# LQ-2549 Terminal intermediate-before-receipt order

- Receipt bytes remain opaque until terminal namespace and root checks succeed.
- A malformed receipt cannot mask or reorder intermediate topology rejection.
- A valid receipt cannot authorize unexpected workspace state.
- Source-commit aggregation starts only after the verifier has fully closed.
- No evidence payload is assembled from a phase with late namespace drift.
- Existing fixed phase ordering and one-execution rule remain unchanged.
