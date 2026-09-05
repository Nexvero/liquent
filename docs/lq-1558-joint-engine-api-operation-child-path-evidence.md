# LQ-1558 Joint engine API operation child path evidence

- Tests reject relative source and acceptance paths.
- Tests reject filesystem-root paths.
- Tests reject alternate child names.
- Tests reject children under different parents.
- Authentic resolved paths remain accepted.
- Final path revalidation remains green.
- Evidence is local and deterministic.
