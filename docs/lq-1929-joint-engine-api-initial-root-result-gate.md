# LQ-1929 Joint engine API initial root result gate

- Initial root result is validated before operation invocation.
- Null, tuples, and arbitrary objects are rejected.
- Invalid result cannot trigger source or registry reads.
- Invalid result cannot invoke acceptance mutation.
- Operation callback receives exact roots only.
- No root attributes are accessed before validation.
- Root failure remains detail-free.
