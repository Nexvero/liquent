# LQ-2085 Joint engine API double slash root rejection

- Double-slash filesystem root is rejected.
- Double-slash subtree roots are rejected.
- Alias equivalence grants no acceptance.
- No descriptor is opened for an alias.
- No clock budget is consumed for an alias.
- No mutation follows alias rejection.
- No fallback canonicalization exists.
