# LQ-2541 Exhaustive close-and-reject helper

- The helper records only whether at least one close attempt failed.
- It continues iterating after every operating-system close error.
- Rejection occurs only after all supplied descriptors were attempted.
- Raw exception text, errno, and descriptor values remain unobservable.
- An empty descriptor sequence completes without rejection.
- The helper performs no retry, fallback, logging, or state retention.
