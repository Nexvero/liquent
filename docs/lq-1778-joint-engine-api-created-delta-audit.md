# LQ-1778 Joint engine API created delta audit

- Mutation delta and closed result now identify one marker.
- Source-derived acceptance binds the same observation.
- Final inventory contains the selected marker exactly once.
- Caller input cannot select a different acceptance.
- Invalid correlation fails before operation success.
- Registry persistence and mutation remain unchanged.
- Created-delta handoff is closed for this slice.
