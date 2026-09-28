# LQ-1508 Descriptor-bound joint engine API source observation

- Each child read captures complete stable descriptor metadata.
- Root state comes from the held owner-private directory descriptor.
- Internal pre/post checks remain mandatory during every read.
- Expected root identity remains independently enforced.
- Snapshot bytes and states are returned as one immutable observation.
- No later path stat supplies source evidence.
- Neutral or malformed source state fails closed.
