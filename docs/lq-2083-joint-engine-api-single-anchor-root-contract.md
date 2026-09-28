# LQ-2083 Joint engine API single anchor root contract

- Direct roots require exact POSIX slash anchor.
- Double-slash anchors are not accepted.
- Root aliases cannot pass shape preflight.
- Validation precedes every clock read.
- Validation precedes root resolution.
- Rejection remains detail-free.
- Public signatures remain unchanged.
