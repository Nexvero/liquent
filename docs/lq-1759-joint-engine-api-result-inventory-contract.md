# LQ-1759 Joint engine API result inventory contract

- Closed results carry a canonical registry inventory.
- Every inventory entry is a complete marker observation.
- Run identities occur at most once in one result.
- Marker generations occur at most once in one result.
- Marker states occur at most once in one result.
- Invalid inventories fail closed without detail.
- Storage and public command behavior remain unchanged.
