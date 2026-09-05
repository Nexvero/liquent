# LQ-1468 Bound joint engine API acceptance readback

- Final marker lookup receives expected acceptance-root identity.
- It checks identity before comparing the durable marker value.
- Same-content registry replacement after record is rejected.
- File sync, directory sync, source revalidation, and time bounds remain.
- The original registry may contain the durable marker after rejection.
- No destructive rollback is attempted across a root replacement.
- Technical errors retain the established unavailable result.
