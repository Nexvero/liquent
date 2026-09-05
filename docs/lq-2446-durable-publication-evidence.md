# LQ-2446 Durable publication evidence

- Focused tests force the first parent synchronization after rename to fail.
- The rollback path restores the private workspace and synchronizes the parent.
- The failed operation leaves no visible output name.
- Source checks retain forward sync and terminal parent/source/output verification.
- Existing child, evidence, inventory, signal, and rollback checks remain active.
- Production readiness remains false; deployment and external publication remain forbidden.
