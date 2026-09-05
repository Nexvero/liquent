# LQ-1635 Joint engine API failure revalidation continuity contract

- Inner failure still triggers outer root revalidation.
- A marker durably written before failure may remain.
- Failure revalidation permits that acceptance state change.
- Root, source, identity, ownership, and topology remain fixed.
- Failure never becomes success through revalidation.
- Original fail-closed outcome is retained.
- No rollback or deletion is attempted.
