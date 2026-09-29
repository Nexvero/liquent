# LQ-2759: Staging promotion reconciliation PostgreSQL acceptance

## Status

Completed as a real PostgreSQL database and real CLI-composition acceptance
audit. The slice adds tests and documentation only; it changes no production
runtime.

## Verified operator chain

The PostgreSQL integration path creates a dedicated throwaway database,
migrates it to the current head and records one exact unknown-effect candidate.
The acceptance then installs private provider and process settings and proves:

`installed` → `ready` → `pending` → `reconciled` → `idle`

The bounded reconciliation performs exactly one provider request. Its exact
committed outcome records the durable reconciliation and removes the candidate
from the unknown-effect index. An independent database engine confirms that the
committed result is visible outside the command's process-owned engine.

The CLI presentation exposes no settings path, endpoint, database URL or
operation identity.

## Closed authority boundary

The audit adds no new production code, command, trigger, scheduler, service or
automation. It does not authorize another reconciliation and does not grant promotion or deployment authority.
Provisioning, provider authorization, promotion approval and deployment remain
separate external operations.
