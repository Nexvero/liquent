# LQ-2573 Duplicate-identity alias rejection

- A mapping cannot present one filesystem object as two phase outputs.
- Evidence binds `artifacts` and `bundle` to the same valid identity tuple.
- The duplicate is rejected without checking whether either path exists.
- A boolean key is separately rejected despite being hashable.
- Both cases prove workspace opening remains unreachable.
- No fallback identity capture or mapping repair occurs.
