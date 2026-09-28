# LQ-2313 candidate-output directory verification gate

- Descriptor verification first validates its current parent directory.
- Symlink, non-directory, foreign owner, or mode drift rejects fail closed.
- File type, mode, link count, size, bytes, and digest then remain required.
- Directory and file checks are independent acceptance conditions.
- Existing output-directory collision prevents Bundle gate continuation.
- Verification repairs neither directory nor descriptor metadata.
- Successful output remains local and explicitly non-promotable.
