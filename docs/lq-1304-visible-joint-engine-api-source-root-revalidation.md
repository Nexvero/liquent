# LQ-1304 Visible joint engine API source root revalidation

- Final validation inspects the still-open directory descriptor.
- It independently inspects the visible path without following symlinks.
- Both observations must match the originally opened root identity.
- Mode, owner, group, link, size, and change timestamps must also agree.
- The descriptor-relative final inventory must remain exactly canonical.
- All validation runs before construction of the public snapshot value.
- Operating-system failures become existing detail-free unavailability.
