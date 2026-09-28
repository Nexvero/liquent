# LQ-2003 Joint engine API clock failure foundation

- Reader, provider, and validator form one boundary.
- Failure policy is independent of clock kind.
- Value policy remains clock-kind-specific.
- Existing unavailable identity is preserved.
- Ordinary exceptions lose provider detail.
- System control flow remains outside normalization.
- No new exception name exists.
