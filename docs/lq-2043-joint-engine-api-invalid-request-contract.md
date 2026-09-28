# LQ-2043 Joint engine API invalid request contract

- Invalid shape means closed request rejection.
- It does not mean neutral persisted absence.
- It does not mean technical filesystem failure.
- Callers receive no failed-field detail.
- No retry or normalization is performed.
- No clock or persistence work follows.
- No new exception is named.
