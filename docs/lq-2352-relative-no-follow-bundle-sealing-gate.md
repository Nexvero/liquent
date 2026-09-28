# LQ-2352 Relative no-follow bundle-sealing gate

- The bundle is opened relative to the bound parent and without following symbolic
  links.
- The same open descriptor supplies type, owner, link-count, and size checks.
- Mode 0600 is applied and synchronized through that descriptor.
- Bundle hashing then reads the same descriptor rather than reopening a path.
- Invalid topology or metadata fails closed without repair.
