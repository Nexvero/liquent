# LQ-2368 Exclusive relative controlled-evidence write gate

- Evidence is opened exclusively with create and no-follow semantics relative to
  the bound workspace descriptor.
- A pre-existing file, symbolic link, or other object is never replaced.
- The open descriptor is forced to mode 0600 and receives the complete canonical
  payload through checked writes.
- File synchronization precedes metadata acceptance.
- No path-based evidence write or post-write chmod is used.
