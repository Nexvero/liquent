# LQ-2275 distribution-pair name/version contract

- The distribution pair belongs to the single project name `liquent`.
- Wheel and sdist filenames each carry one validated package version.
- Both filenames must identify exactly the same version.
- Matching bytes under renamed or mismatched artifacts are insufficient.
- Version identity is derived from controlled filenames, never caller input.
- Existing embedded wheel and sdist-root checks remain independent.
- This identity grants no installation, signing, or publication authority.
