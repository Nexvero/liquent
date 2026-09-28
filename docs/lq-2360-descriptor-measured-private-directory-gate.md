# LQ-2360 Descriptor-measured private-directory gate

- Directory type, mode, owner, device, and inode are measured with `fstat` on the
  successfully opened no-follow descriptor.
- The directory must be owned by the current user and have mode exactly 0700.
- Device and inode form the identity consumed by later bound operations.
- Failed or invalid measurements close the descriptor and fail closed.
- No permission repair or ownership change is attempted.
