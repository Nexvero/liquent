# LQ-1768 Source acceptance unique joint engine API inventory

- Source authority and envelope derive the expected acceptance.
- Exactly one final marker must carry that acceptance.
- Duplicate source acceptances are rejected at construction.
- Different valid accepted runs may remain alongside it.
- Caller-supplied acceptance claims grant no trust.
- Correlation uses retained verified source evidence only.
- No additional registry mutation is introduced.
