# LQ-2564 Capture workspace-identity preopen gate

- Capture applies the shared identity validator to its workspace identity.
- Boolean, negative, malformed, and noninteger tuples reject immediately.
- Validation occurs before opening the workspace or resolving a child.
- A real matching path cannot compensate for an invalid identity fact.
- No descriptor exists or requires cleanup on this rejection path.
- The existing fixed controlled message remains the only result.
