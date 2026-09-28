# LQ-2586 Single intermediate verification-authority evidence

- Source evidence requires exactly two map-verifier calls around gate execution.
- It requires exactly one child-identity helper call in the phase loop.
- It forbids the former retained identity iteration from that loop.
- Behavioral replacement, topology, cleanup, and publication tests remain active.
- Complete project regression and diff hygiene are required for handoff.
- Production readiness remains false; publication and deployment stay forbidden.
