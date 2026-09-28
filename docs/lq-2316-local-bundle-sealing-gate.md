# LQ-2316 local bundle-sealing gate

- Sealing requires the previously validated private parent-directory identity.
- The bundle is opened read-only without following symbolic links.
- Descriptor metadata must satisfy owner, type, link, and size bounds.
- Mode is set to `0600` and file state is synchronized.
- SHA-256 is streamed from the held descriptor in bounded chunks.
- Size and mode are checked again before descriptor closure.
- Parent device and inode must remain identical after sealing.
