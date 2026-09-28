# LQ-1365 Joint engine API operation failure revalidation evidence

- Tests record exactly one final validation after successful execution.
- Tests record exactly one final validation after an inner exception.
- An unchanged boundary preserves the original inner failure.
- Root replacement during failure becomes closed boundary rejection.
- Source and acceptance replacement receive separate evidence.
- Existing successful lifecycle tests remain green.
- Focused verification treats deprecation warnings as failures.
