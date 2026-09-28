# LQ-1750 Joint engine API closed accept result audit

- LQ-1747 through LQ-1749 close accept result shape.
- Positional source and registry unpacking is eliminated.
- Success finalization consumes named immutable fields.
- Invalid result shape cannot enter live rechecks.
- Failure remains fail-closed and detail-free.
- No persistence or protocol format changed.
- Source correlation remains next.
