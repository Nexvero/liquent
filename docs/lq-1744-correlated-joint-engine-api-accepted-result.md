# LQ-1744 Correlated joint engine API accepted result

- Constructor decodes authority from source snapshot.
- It rebuilds acceptance from authority and envelope.
- Marker acceptance must equal rebuilt acceptance exactly.
- Source and marker complete states remain retained.
- Outer rereads use named source and marker fields.
- Retained snapshot drives final freshness verification.
- No normalization or alternate expectation exists.
