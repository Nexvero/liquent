# LQ-1321 Joint engine API ancestor symlink evidence

- Tests create a real parent containing a canonical source root.
- A sibling symlink aliases that parent without changing target content.
- Loading through the alias rejects for all source-layout generations.
- Separate tests retain explicit leaf-symlink rejection coverage.
- Real parent and real leaf paths provide positive controls.
- Existing final root-rebinding evidence remains green.
- Focused evidence runs under strict warning handling.
