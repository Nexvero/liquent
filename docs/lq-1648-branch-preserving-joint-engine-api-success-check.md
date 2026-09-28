# LQ-1648 Branch-preserving joint engine API success check

- Accept-once installs the inventory equality check.
- Read-only audit paths remain unchanged.
- Operation result still propagates through the wrapper.
- Public accept-once continues returning no value.
- Check failure follows the normal failure branch.
- Successful check advances to exact final validation.
- No CLI argument or exit code changes.
