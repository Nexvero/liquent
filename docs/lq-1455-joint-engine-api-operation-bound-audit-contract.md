# LQ-1455 Joint engine API operation-bound audit contract

- Operation audit resolves source and acceptance children once.
- Registry-only audit binds its acceptance-root read.
- Accepted-source audit binds both source and acceptance reads.
- Inner readers consume the resolved identities unchanged.
- A swap after resolution must not establish a new audit basis.
- Final operation-root revalidation remains an added invariant.
- Failures reveal no path, identity, or marker detail.
