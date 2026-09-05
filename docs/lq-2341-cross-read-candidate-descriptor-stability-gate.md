# LQ-2341 Cross-read candidate-descriptor stability gate

- Device, inode, size, and modification time must remain stable across reading.
- Read bytes must exactly equal canonical candidate facts and hash to the bound
  release-candidate SHA-256 value.
- Parent identity is checked on the open directory and again after descriptors
  close, so directory replacement fails closed.
- No retry or normalization accepts a changing descriptor.
- The verified descriptor remains local evidence only.
