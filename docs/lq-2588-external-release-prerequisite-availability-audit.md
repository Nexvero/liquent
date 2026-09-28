# LQ-2588 External release-prerequisite availability audit

- No `LIQUENT_TEST_DATABASE_URL` is available to this process.
- No Docker executable is available in the current execution environment.
- No Grype executable is available in the current execution environment.
- PostgreSQL integration, image build, and vulnerability scan cannot be claimed.
- No environment value, DSN, credential, image, or registry target was printed.
- Missing prerequisites are blockers, not skipped successful release gates.
- Installing tools or creating infrastructure is outside this local audit.
- Production readiness therefore remains false.
