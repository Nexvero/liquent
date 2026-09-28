# LQ-2531 Phase-output capture descriptor lifecycle

- Child and workspace descriptors remain local to one capture invocation.
- The child receives its close attempt before the workspace descriptor.
- Both closes are attempted even when the first one fails.
- Any close failure becomes the existing controlled rejection.
- Raw descriptor and operating-system details never leave the boundary.
- No descriptor is cached, transferred, or reused as later authority.
