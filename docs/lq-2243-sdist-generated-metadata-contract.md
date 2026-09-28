# LQ-2243 sdist generated-metadata contract

- Eight generated sdist files carry only reviewed redundant package facts.
- Root and egg-info PKG-INFO are byte-identical to wheel METADATA.
- Egg-info entry points and top-level roots are byte-identical to wheel files.
- Requirements and egg-info setup configuration have canonical fixed bytes.
- SOURCES.txt covers every sdist file except root PKG-INFO and setup.cfg.
- Generated metadata is hashed as one ordered internal fact.
- The contract adds no build, installation, or publication authority.
