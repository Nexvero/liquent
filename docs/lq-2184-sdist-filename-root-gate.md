# LQ-2184 sdist filename root gate

- Root derivation reads only the exact final path component.
- Empty versions and foreign project prefixes are rejected.
- Separators, spaces, controls, and normalization aliases are excluded.
- Version letters, digits, dot, underscore, plus, and hyphen are allowed.
- The derived root is an internal validator fact.
- Archive content cannot override that root through PAX metadata.
- Rejection remains detail-limited at the release gate.
