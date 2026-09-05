# LQ-2428 Phase-output identity capture gate

- The controller maps only distribution, entry-point, sdist, and bundle phases.
- Each mapped phase must leave its exact expected private directory present.
- Identity capture is descriptor-relative to the already bound workspace root.
- The child must be a current-user-owned real directory with mode 0700.
- Duplicate capture, missing output, or an unexpected child name fails closed.
- Unmapped phases cannot create trusted phase-output identity state.
