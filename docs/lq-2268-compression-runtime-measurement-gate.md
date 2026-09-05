# LQ-2268 compression-runtime measurement gate

- The runtime gate measures Python 3.12.14 exactly.
- It measures zlib build version 1.2.12 independently.
- It also measures the loaded zlib runtime as version 1.2.12.
- Any mismatch rejects before tests or artifact construction begin.
- Package build-tool locks remain an additional independent requirement.
- Measurements are local facts and are not caller-supplied allow values.
- Rejection remains detail-limited at the controlled preflight boundary.
