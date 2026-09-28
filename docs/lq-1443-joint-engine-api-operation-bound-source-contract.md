# LQ-1443 Joint engine API operation-bound source contract

- Operation accept resolves source and acceptance children once.
- Their descriptor identities are immutable inputs to inner acceptance.
- Inner verification must consume both resolved identities unchanged.
- A path swap after resolution must not establish a new source basis.
- Operation-root final revalidation remains an additional invariant.
- Failure creates no acceptance marker and reveals no root details.
- Standalone source and one-shot boundaries remain independently usable.
