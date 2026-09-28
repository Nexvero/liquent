# LQ-1955 Joint engine API accept snapshot completion

- Accept performs two outer snapshot verifications.
- First uses completion-verification UTC instant.
- Second uses final UTC instant.
- Both verify the same retained snapshot.
- Both require normal none completion.
- Durable marker remains on late completion rejection.
- Existing duration policy remains unchanged.
