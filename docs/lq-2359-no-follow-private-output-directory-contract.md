# LQ-2359 No-follow private output-directory contract

- Private candidate-output identity is established by opening the directory itself.
- The open uses directory-only and no-follow semantics.
- A symbolic link, non-directory object, missing path, or inaccessible path is
  rejected without fallback resolution.
- No path metadata snapshot alone establishes directory authority.
- The resulting identity remains local and non-promotable.
