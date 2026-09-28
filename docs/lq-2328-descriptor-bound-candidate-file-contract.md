# LQ-2328 Descriptor-bound candidate file contract

- Each expected candidate file is opened relative to the bound directory and
  without following symbolic links.
- The opened object must be a non-empty regular file owned by the current user,
  have mode 0600, and have exactly one link.
- Hashing and byte counting use the same open file descriptor.
- Caller-controlled paths, inferred permissions, and repair are not accepted.
- Failure remains detail-free at the existing local gate boundary.
