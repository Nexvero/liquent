# LQ-2621 Post-merge main synchronization

- Pull request #128 was squash-merged and closed after all four required checks passed.
- The resulting immutable `main` commit is `2a5a5b07ab6cee951dbead4c25868701e134c7b7`.
- Its exact source tree is `8a0cdc71327250999d1f70405f798ce35a95e890`.
- The accepted pull-request head was `7a07621a89c6fe4f835076ead07f93407e72f4a5`.
- Branch `codex/lq-post-merge-release` starts directly from that merged `main` commit.
- The former integration branch is historical input and no longer identifies current release work.
- Squashing changed commit identity even where source bytes remain equal.
- Evidence bound to code commit `d273c9a` therefore remains historical and cannot silently authorize the merge commit.
- The merged commit requires fresh candidate-bound preflight, package, image, smoke, and scan evidence before signing.
- This synchronization records no signer approval, registry target, provider authority, staging acceptance, or deployment approval.
- No tag, release, publication, environment mutation, or deployment is performed by this slice.
