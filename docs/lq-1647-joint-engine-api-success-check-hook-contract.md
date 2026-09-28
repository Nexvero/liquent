# LQ-1647 Joint engine API success-check hook contract

- Wrapper supports one internal post-capture success check.
- Check receives resolved roots and operation result.
- It runs only after inner operation success.
- It completes before final root validation.
- Failure prevents completed-success state.
- Existing failure revalidation then remains active.
- Hook grants no authority and performs no implicit write.
