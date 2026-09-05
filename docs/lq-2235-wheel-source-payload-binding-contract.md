# LQ-2235 Wheel source-payload binding contract

- Every installable package payload equals one reviewed source-tree file.
- Wheel member names and source-relative names form the same exact set.
- Matching names with changed bytes are insufficient.
- Source files are regular non-symlink Python or Mako files.
- Generated dist-info remains governed by separate metadata gates.
- Binding occurs inside preflight from its owned source root.
- The contract adds no import, execution, or installation authority.
