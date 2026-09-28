# LQ-2543 Intermediate verifier shared cleanup

- Intermediate verification delegates all retained closes to the same helper.
- Its bounded child collection precedes the workspace descriptor in order.
- Partial child-open failure still closes every child opened before rejection.
- Successful verification is not observable until cleanup also succeeds.
- Existing descriptor-retention and terminal identity checks remain unchanged.
- No verifier descriptor survives intentionally into a later phase.
