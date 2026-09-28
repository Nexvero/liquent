# LQ-1992 Joint engine API three-stage audit monotonic

- Registry audit validates all three reads.
- Accepted-source audit validates all three reads.
- Initial read precedes operation-root work.
- Final read follows first convergence checks.
- Terminal read follows terminal checks.
- Both modes retain the same duration bound.
- Audit remains read-only.
