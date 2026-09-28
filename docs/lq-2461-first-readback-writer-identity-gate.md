# LQ-2461 First-readback writer-identity gate

- The first no-follow readback receives identity captured by the writer.
- Its open file descriptor must match that device and inode before bytes are accepted.
- Returned stable readback identity must equal the writer identity again.
- Replacement between writer close and first readback therefore fails closed.
- Only that verified identity enters precommit inventory and publication state.
- Payload equality remains independently mandatory.
