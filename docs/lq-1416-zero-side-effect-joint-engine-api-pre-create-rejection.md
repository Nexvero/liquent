# LQ-1416 Zero-side-effect joint engine API pre-create rejection

- Shared root validation observes only descriptor metadata.
- It performs no marker listing, read, creation, or deletion.
- Rejection returns before record marks any file as created.
- Existing cleanup remains reserved for failures after exclusive creation.
- The held registry descriptor closes through normal record finalization.
- The visible validation descriptor closes within the gate itself.
- Error conversion remains detail-free.
