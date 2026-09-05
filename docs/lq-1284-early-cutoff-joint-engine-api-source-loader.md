# LQ-1284 Early cutoff joint engine API source loader

- A single helper owns ordered loading and cumulative accounting.
- It validates paired canonical names and individual limits before loading.
- Each completed child read immediately updates the aggregate total.
- Overflow raises before the loop can advance to another source.
- All public source-set loaders delegate to this common helper.
- Existing final root metadata and inventory checks remain after success.
- Technical failures retain the existing detail-free boundary.
