# LQ-2691 — Persistent staging session-set registry

LQ-2691 adds a secret-free persistent registry for pre-provisioned staging
Research-index session sets. Each retained fact contains only an opaque set ID,
one globally non-reused revision, and active/inactive lifecycle state.

The read-only resolver requires both exact opaque values and returns only the
bound registration. Unknown, inactive, revoked, or stale facts are neutral
absence. Storage and decoding failures collapse to one detail-free technical
unavailability. Later lifecycle changes affect every later lookup.

No session value, password, token, provider identity, user, workspace, role,
membership, permission, capability, or allow boolean is stored or accepted.
The registry grants no authority and exposes no create, update, delete, rotate,
login, acquisition, CLI, deployment, or promotion operation. Provisioning,
mutation, secret resolution, concrete acquisition, and promotion remain later
slices.
