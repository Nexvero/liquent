# LQ-1870 Joint engine API accept inventory foundation audit

- One shared validator closes both inventory handoffs.
- Closed accept result reuses that validator again.
- Before, after, and retained inventory semantics align.
- Validation precedes each dependent decision.
- All malformed shapes use one boundary failure.
- Persistence and observer behavior remain unchanged.
- Foundation is ready for typed delta comparison.
