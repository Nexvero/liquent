# LQ-2000 Shared joint engine API clock reader

- One private reader composes provider and validator.
- The provider is invoked exactly once.
- Its value is validated exactly once.
- A valid value is returned unchanged.
- No clock kind is inferred.
- No persistence work occurs.
- No public port is added.
