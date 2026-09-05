# LQ-1324 Joint engine API layout component walk composition

- Each public loader delegates root acquisition to one component walker.
- Existing root metadata checks consume the returned final descriptor.
- Existing bounded child loading remains descriptor-relative to that root.
- Existing visible-path identity comparison still closes later rebinding.
- Snapshot construction remains specific to each canonical layout.
- No CLI option or runtime configuration controls traversal behavior.
- The change composes without altering cryptographic semantics.
