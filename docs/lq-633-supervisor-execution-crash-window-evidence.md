# LQ-633 — Supervisor execution crash-window evidence

## Status

Implemented as executable evidence over real journal, runtime, gate, engine, and
recorded artifact domain values.

## Matrix

The tests prove:

- running engine without Consumed waits for child consumption;
- running engine with Consumed is capability in flight;
- terminal engine with Consumed but no Terminal is ambiguous and blocked;
- Terminal plus running engine waits for direct engine terminality;
- Terminal plus terminal engine is ready for parent terminal correlation;
- a `running` journal without Consumed is divergent;
- a different Consumed Release ID is divergent.

Every matrix result denies child start, Release publication, and capability
execution. Malformed input remains detail-free technical unavailability.

The focused run also retains the child sequence and existing parent release,
inspect, and terminal contracts. It performs no database, Docker, network,
subprocess, migration, CLI, or deployment work.

LQ-634 closes the ownership and reconciliation strand.
