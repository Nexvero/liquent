# LQ-2239 sdist source-payload contract

- Every non-generated sdist file equals one reviewed repository file.
- Archive and repository source-name sets are exact peers.
- Allowed source scope is README, pyproject, package source, and tests.
- Documentation, tools, caches, secrets, and foreign roots are excluded.
- Eight fixed build-metadata files remain separately generated facts.
- Name equality and byte equality are both mandatory.
- The contract adds no extraction, installation, or publication authority.
