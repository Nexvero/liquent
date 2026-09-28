# LQ-1497 Descriptor-derived joint engine API marker state

- Read observation captures state before reading marker bytes.
- Stable metadata comparison confirms it did not change during read.
- Record observation captures state after durable post-write checks.
- Both paths use the already-open no-follow marker descriptor.
- No later path lookup supplies observation state.
- Registry-root validation remains independently required.
- Missing marker still returns neutral absence without state.
