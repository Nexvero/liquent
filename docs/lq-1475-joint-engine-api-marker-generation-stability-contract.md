# LQ-1475 Joint engine API marker generation stability contract

- Accepted-source audit must verify one concrete marker generation.
- First and final observations must match in value and file identity.
- Equal bytes in a newly created marker are not continuity evidence.
- Registry-root continuity alone does not prove marker continuity.
- Marker generation remains separate from source snapshot identity.
- Replacement fails closed without naming filesystem details.
- No mutation or repair is performed by the audit.
