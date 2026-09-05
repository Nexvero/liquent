# LQ-1668 Retained-source joint engine API final verification

- Success check retains the original source observation.
- Its snapshot is passed to pure run-bound verification.
- Final UTC time is used without normalization.
- Run signature, image authority, policy, and evidence revalidate.
- Receipt and evidence ages are recomputed.
- No source reload substitutes another snapshot.
- Verification performs no write.
