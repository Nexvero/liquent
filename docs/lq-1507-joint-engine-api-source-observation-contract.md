# LQ-1507 Joint engine API source observation contract

- Source observation combines snapshot, root state, and child states.
- All facts derive from descriptors used for the source read.
- Fourteen fixed-layout children must be represented exactly.
- State is immutable evidence and grants no authority.
- Malformed state fails through the existing unavailable boundary.
- Representation reveals no source content or filesystem facts.
- Existing snapshot-only loading remains compatible.
