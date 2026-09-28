# LQ-2519 Intermediate child-descriptor lifecycle

- One descriptor is retained for every expected directory in an invocation.
- All retained child descriptors close before the workspace descriptor closes.
- Successful, rejected, and operating-system-error paths share that cleanup.
- Descriptors do not escape the verifier or become reusable authority tokens.
- No phase callback executes while a verifier invocation remains active.
- Later invocations reopen and revalidate current system-of-record state.
