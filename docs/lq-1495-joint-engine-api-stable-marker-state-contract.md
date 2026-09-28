# LQ-1495 Joint engine API stable marker state contract

- Marker continuity includes identity and immutable descriptor state.
- State covers mode, ownership, links, size, and change timestamps.
- All state fields come from the descriptor that supplied marker bytes.
- Identity must equal the device and inode prefix of state.
- Malformed or internally inconsistent state fails closed.
- State is evidence, never an authorization or caller input.
- Representation continues revealing no filesystem facts.
