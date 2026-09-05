# LQ-1849 Joint engine API accept handoff type evidence

- Tests reject null, tuple, and object handoffs.
- Tests reject a bare acceptance value.
- Rejection occurs before post-mutation inventory read.
- Foreign return after a real mutation remains rejected.
- Durable marker is preserved on that failure path.
- Exact canonical observation still completes.
- All focused warnings are treated as errors.
