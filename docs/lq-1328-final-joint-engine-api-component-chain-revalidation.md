# LQ-1328 Final joint engine API component chain revalidation

- Final root validation opens the absolute component chain a second time.
- Every final component open retains directory, no-follow, and close-on-exec.
- The resulting leaf metadata is compared with initial and held descriptors.
- Full stable root metadata and exact held inventory must still agree.
- The final traversal descriptor closes before validation returns.
- Failure paths close every descriptor owned by final traversal.
- Existing loaders invoke this through their common root validator.
