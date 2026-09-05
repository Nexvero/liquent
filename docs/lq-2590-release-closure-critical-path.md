# LQ-2590 Release-closure critical path

- Further micro-hardening is paused in favor of release-closing evidence.
- First provide one authorized disposable PostgreSQL test DSN.
- Then run the complete PostgreSQL-required controlled preflight successfully.
- Provide Docker and build the fixed release image from the accepted candidate.
- Provide Grype and complete the required vulnerability-policy scan.
- Generate and verify signed external release evidence without granting deploy.
- Execute the documented staging acceptance chain against controlled targets.
- Reinventory all files, review the cumulative diff, and update final status.
- Branching, staging, commit, push, publication, and deployment require authority.
- Until every mandatory gate succeeds, `production_ready` remains false.
