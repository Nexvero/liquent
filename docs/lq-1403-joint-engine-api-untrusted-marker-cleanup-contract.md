# LQ-1403 Joint engine API untrusted marker cleanup contract

- A marker is not trusted until descriptor-bound readback succeeds.
- Verification failure before trust triggers best-effort marker removal.
- Cleanup addresses only the exact newly created descriptor-relative name.
- The registry directory is synchronized after successful removal.
- Cleanup failure does not convert the original operation to success.
- No already trusted or previously existing marker is removed.
- Failure remains detail-free registry unavailability.
