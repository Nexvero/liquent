# LQ-1979 Joint engine API three-stage accept UTC

- Initial UTC read precedes operation execution.
- Verification UTC read follows first convergence checks.
- Final UTC read follows final monotonic reading.
- All three values cross exact UTC validation.
- Time must remain nondecreasing across decisions.
- Late invalid clock result preserves durable marker.
- Existing duration policy remains unchanged.
