# LQ-2558 Exact device-inode tuple validation

- A valid identity contains exactly device and inode positions.
- Both positions require exact integer runtime types and nonnegative values.
- Boolean values are rejected despite Python integer subclass behavior.
- Lists and other iterable containers are not accepted as identity facts.
- No coercion, parsing, normalization, or default value is permitted.
- Kernel-derived valid tuples retain their original values unchanged.
