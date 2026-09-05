# LQ-2555 Expected-map alias-mutation isolation

- Evidence mutates the source dictionary during the first workspace listing.
- The mutation replaces its correct captured identity with a false tuple.
- Running verification still succeeds from its earlier immutable snapshot.
- The caller-owned source dictionary remains mutated and visibly distinct.
- No filesystem observation consults that changed alias afterward.
- This proves decision consistency without adding synchronization authority.
