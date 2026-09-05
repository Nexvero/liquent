# LQ-2492 Second target-absence gate

- The output name is checked once during initial publication validation.
- It is checked again immediately after precommit child verification.
- The second check is descriptor-relative and does not follow symbolic links.
- Any file, directory, link, or special entry at the name fails closed.
- Existing content is neither opened for writing nor removed.
- Relative rename begins only after this second absence observation.
