# LQ-1987 Joint engine API validated monotonic contract

- Every outer monotonic read crosses one validator.
- Runtime type must be exact float.
- Values must be finite and nonnegative.
- Null, boolean, integer, negative, and nonfinite values fail.
- Validation precedes duration comparison.
- Failure remains detail-free.
- Public command behavior remains unchanged.
