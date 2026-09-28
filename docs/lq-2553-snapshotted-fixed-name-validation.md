# LQ-2553 Snapshotted fixed-name validation

- Fixed-name validation applies to the local expectation snapshot.
- Every key must belong to the four controller-defined phase outputs.
- An unsupported snapshotted name rejects before workspace opening.
- Later removal of that key from the source mapping cannot change rejection.
- Later addition to the source mapping cannot expand the running expected set.
- Caller-selected names never become trusted intermediate topology.
