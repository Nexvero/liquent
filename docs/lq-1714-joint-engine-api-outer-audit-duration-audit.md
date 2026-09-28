# LQ-1714 Joint engine API outer audit duration audit

- LQ-1711 through LQ-1713 bound read-only audit duration.
- Inner accepted-source duration remains independently bounded.
- Registry mode now has an explicit operation bound.
- Root sandwich and evidence rechecks are included.
- Failure remains fail-closed and detail-free.
- No marker or source mutation is performed.
- Outer accepted freshness remains next.
