# LQ-1548 Closed joint engine API marker link and size

- Observation construction checks link count before use.
- It derives expected size from the contained acceptance value.
- Hard-linked marker state is rejected.
- Zero, oversized, and off-by-one sizes are rejected.
- Descriptor read limits remain independently enforced.
- Existing marker encoding remains unchanged.
- Technical failure stays detail-free.
