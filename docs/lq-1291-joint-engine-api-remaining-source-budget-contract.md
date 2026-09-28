# LQ-1291 Joint engine API remaining source budget contract

- Every child read is bounded by the aggregate budget still available.
- The remaining amount is derived internally from completed source bytes.
- A caller cannot supply or alter that per-read allowance.
- The effective child limit is the lesser of its own and remaining limits.
- Oversized content fails within the bounded descriptor-relative reader.
- Previously completed values never exceed the aggregate ceiling.
- Existing snapshot and technical-unavailability boundaries remain unchanged.
