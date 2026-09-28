# LQ-2223 Wheel dependency identity contract

- Installable dependency metadata equals the reviewed Liquent dependency set.
- Runtime requirements and optional-extra requirements are exact ordered facts.
- Requires-Python is exactly >=3.10.
- License-Expression is exactly LicenseRef-Proprietary.
- Unreviewed external or dynamic requirements fail closed.
- Wheel metadata cannot silently broaden installed capability.
- The contract adds no dependency installation or publication operation.
