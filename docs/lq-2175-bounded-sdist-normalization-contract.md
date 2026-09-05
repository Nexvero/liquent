# LQ-2175 Bounded sdist normalization contract

- Normalization consumes only explicitly bounded archive resources.
- Compressed bytes, members, names, files, and total payload are limited.
- Bounds are fixed repository policy rather than caller input.
- Declared file sizes must equal bytes actually read.
- A bound violation fails before replacement of the source artifact.
- Input symlinks are never followed as release artifacts.
- The contract grants no publication or installation authority.
