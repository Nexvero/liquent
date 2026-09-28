# LQ-2348 No-follow candidate-identity input gate

- Each identity input is opened relative to its bound parent without following
  symbolic links.
- The open object must be a private regular file owned by the current user, with
  one link, non-zero size, and its existing artifact-specific size ceiling.
- Bundle and evidence bytes are obtained only from those open descriptors.
- Symlink, hardlink, type, ownership, mode, or size drift fails closed.
- No repair or alternate input lookup is attempted.
