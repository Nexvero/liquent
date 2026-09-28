# LQ-2412 Configuration-independent Pip-install gate

- Pip runs in isolated mode with index access and dependency handling disabled.
- Version checks and bytecode compilation are disabled for bounded deterministic output.
- The command receives one verified wheel path and one pre-created private target path.
- It cannot select a requirement, alternate package source, or caller-controlled target.
- A non-zero result remains a detail-limited local gate rejection.
- Installed content is subsequently normalized and measured by the existing tree gate.
