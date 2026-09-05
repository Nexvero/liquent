# LQ-2240 sdist source-tree enumerator

- README.md and pyproject.toml are exact root source facts.
- Package enumeration covers .py and .mako below both src roots.
- Test enumeration covers packaged test_*.py files below tests.
- Symlinked roots or candidate files fail closed.
- Generated egg-info, PKG-INFO, and setup.cfg are not source candidates.
- Missing and additional archive source paths are both rejected.
- Enumeration remains dynamic for the reviewed source checkout.
