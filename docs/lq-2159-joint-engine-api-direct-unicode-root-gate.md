# LQ-2159 Joint engine API direct Unicode root gate

- Direct roots must render as exact NFC.
- Direct roots reject Unicode control characters.
- Direct roots reject Unicode format characters.
- Direct roots reject surrogate encoding.
- Visible canonical Unicode remains accepted.
- No normalization fallback exists.
- Root authority remains downstream.
