# LQ-1975 Joint engine API validated UTC contract

- Every outer UTC read crosses one validator.
- Runtime type must be exact datetime.
- Timezone awareness and zero UTC offset are mandatory.
- Naive, null, numeric, and non-UTC values are rejected.
- Validation precedes every time comparison.
- Failure remains detail-free.
- Public command behavior remains unchanged.
