# LQ-2591 Disposable local PostgreSQL runtime

- PostgreSQL 16 was already installed outside the default process search path.
- One isolated cluster was initialized below `/private/tmp/liquent-pg-lq2591`.
- It listens only on local port 55432 and contains database `liquent_test`.
- Host and local authentication are trust-only inside this disposable boundary.
- The server session timezone is explicitly UTC.
- No existing cluster, database, user, volume, or application data was touched.
- The cluster exists only to complete the required integration evidence.
- Its later shutdown and removal remain separate explicit cleanup actions.
