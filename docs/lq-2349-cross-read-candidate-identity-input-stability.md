# LQ-2349 Cross-read candidate-identity input stability

- Device, inode, size, and modification time are compared before and after each
  identity-input read.
- The observed byte count must equal the stable descriptor size.
- Evidence bytes must hash to the previously bound verification digest before
  canonical candidate facts are formed.
- Bundle bytes provide the bound bundle size and digest from the same read.
- Changing inputs cannot be normalized into a candidate identity.
