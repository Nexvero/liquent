# LQ-1776 Delta-bound joint engine API accept result

- Accept operation constructs the closed result after mutation.
- Its locally observed created marker remains authoritative.
- Result derivation must reproduce that exact observation.
- Equality covers acceptance, identity, and marker state.
- Mismatch fails before the success callback begins.
- Successful results preserve the complete final inventory.
- Public return value remains no value.
