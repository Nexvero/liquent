# LQ-1294 Joint engine API remaining source budget audit

- Aggregate enforcement now constrains the overflowing read itself.
- The loader no longer first retains a complete over-budget child value.
- At most one bounded detection byte can establish child oversize.
- Existing individual source bounds are not relaxed or replaced.
- Failure still yields no provenance snapshot or partial result.
- Focused implementation and regression evidence passes.
- External staging readiness remains a separate evidence requirement.
