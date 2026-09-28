# LQ-1393 Joint engine API acceptance root mutation evidence

- Tests cycle registry mode from private to broader and back.
- Marker load rejects the resulting ctime discontinuity.
- Registry inspection independently rejects the same mutation.
- Separate tests touch the root timestamp during each read operation.
- Both read paths reject despite unchanged device and inode identity.
- Unchanged operations provide positive controls.
- Focused mutation evidence passes under strict warnings.
