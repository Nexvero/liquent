# LQ-2197 sdist wheel identity gate

- Roundtrip begins only after cross-phase sdist continuity succeeds.
- Rebuilt wheel bytes must equal direct wheel bytes exactly.
- The existing wheel parser rechecks rebuilt archive integrity.
- The reported roundtrip hash is derived from those accepted bytes.
- Missing, additional, or changed wheel output fails closed.
- Source archive structure and hash reporting remain mandatory.
- Later entry-point and bundle gates remain unchanged.
