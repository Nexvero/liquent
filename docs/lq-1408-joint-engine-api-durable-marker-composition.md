# LQ-1408 Joint engine API durable marker composition

- Canonical acceptance encoding occurs before exclusive marker creation.
- Bounded writes complete through one read-write descriptor.
- File synchronization precedes exact descriptor-bound readback.
- Successful readback advances the marker to trusted local state.
- Directory synchronization durably publishes the created name.
- Final no-follow registry-root validation closes path rebinding.
- Descriptor closure executes for every success and failure path.
