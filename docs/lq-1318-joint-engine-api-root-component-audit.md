# LQ-1318 Joint engine API root component audit

- Source-root opening no longer follows uninspected parent symlinks.
- Descriptor-relative traversal covers the complete absolute path chain.
- Intermediate descriptors have explicit bounded lifetimes.
- Final path identity revalidation remains additive after source capture.
- Public loader signatures and snapshots remain unchanged.
- Focused component-walk evidence passes with architecture guardrails.
- External staging evidence remains outside this local hardening slice.
