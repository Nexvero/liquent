# LQ-2307 candidate-descriptor file-metadata contract

- The candidate descriptor is one regular non-symlink filesystem object.
- Its exact permission mode is owner-read/write only, `0600`.
- Exactly one directory entry may link to its inode after publication.
- Payload size is positive and at most 4096 bytes.
- Content identity remains the complete-file SHA-256.
- Metadata validity grants no signing or promotion authority.
- Ownership identities and platform-specific attributes remain out of scope.
