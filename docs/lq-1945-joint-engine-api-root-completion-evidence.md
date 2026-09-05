# LQ-1945 Joint engine API root completion evidence

- Tests reject object, boolean, and tuple completions.
- Read-only success rejects foreign completion.
- Accept success rejects foreign completion.
- Durable marker remains after accept rejection.
- Failure revalidation also rejects foreign completion.
- Mutation allowance forwarding remains exact.
- All focused warnings are treated as errors.
