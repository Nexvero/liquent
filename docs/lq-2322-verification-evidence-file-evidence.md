# LQ-2322 verification-evidence file evidence

- Tests atomically create one private verification report.
- Tests prove exact mode `0600` and link count one.
- Permission drift is rejected.
- Payload-byte drift is independently rejected.
- A second hard link is independently rejected.
- Existing canonical rendering and stale-quality tests remain intact.
- External signing and publication evidence remain open; production_ready=false.
