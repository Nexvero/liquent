# LQ-1308 Joint engine API source root replacement gate

- One shared final-root helper owns descriptor and path comparison.
- It uses non-following path metadata to expose symlink replacement.
- Original, descriptor-final, and path-final facts must be identical.
- Exact final names are checked against the open descriptor itself.
- Replacement rejection precedes immutable snapshot construction.
- Each public source loader invokes the same gate exactly once.
- No polling, retry, recovery, or alternate-root fallback is introduced.
