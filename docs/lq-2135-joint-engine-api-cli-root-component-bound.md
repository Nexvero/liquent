# LQ-2135 Joint engine API CLI root component bound

- Every component is bounded to 255 UTF-8 bytes.
- Boundary-sized components remain accepted.
- Oversized components fail before Path construction.
- Empty and navigation components remain rejected.
- Repeated separators remain rejected.
- No truncation is performed.
- No component hashing is introduced.
