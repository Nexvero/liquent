# LQ-2407 Installed-distribution identity contract

- Installed evidence represents exactly one distribution named `liquent`.
- Its version must equal the version bound by the verified distribution pair.
- Its identity includes every console-script name and target from the verified wheel.
- Entries are sorted canonically and duplicate command names fail closed.
- The resulting SHA-256 binds schema, package name, version, names, and targets.
- This identity is local release evidence and grants no publication authority.
