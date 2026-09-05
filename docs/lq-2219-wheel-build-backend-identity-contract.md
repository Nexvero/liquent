# LQ-2219 Wheel build-backend identity contract

- Accepted wheel metadata identifies the reviewed locked build backend.
- Core metadata version is exactly 2.4.
- Generator identity is exactly setuptools 80.10.2.
- Wheel control headers have one canonical set and order.
- Duplicate or alternate backend claims fail closed.
- Backend identity supplements rather than replaces byte reproducibility.
- The contract adds no installation or publication authority.
