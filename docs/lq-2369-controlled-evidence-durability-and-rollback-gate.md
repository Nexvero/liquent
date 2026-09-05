# LQ-2369 Controlled-evidence durability and rollback gate

- The synchronized evidence descriptor must report a regular current-user-owned
  mode-0600, single-link file of the exact payload size.
- The workspace directory is synchronized before later workspace publication.
- Workspace device and inode must remain stable throughout evidence creation.
- Any failure after creation removes evidence relative to the same descriptor.
- No uncertain or partially durable evidence is treated as success.
