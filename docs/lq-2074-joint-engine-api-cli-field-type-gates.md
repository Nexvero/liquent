# LQ-2074 Joint engine API CLI field type gates

- Root field must satisfy Path runtime policy.
- Text root substitutes are not accepted.
- Mode runtime type must be exact string.
- Boolean and numeric modes are not accepted.
- Mode value must belong to the closed inventory.
- Validation grants no operation authority.
- Direct preflight remains authoritative.
