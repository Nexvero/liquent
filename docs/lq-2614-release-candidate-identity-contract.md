# LQ-2614 Release-candidate identity contract

- Code commit `d273c9af6b8cb5ad62fed399821b5570beef906b` owns the completed preflight, image, smoke, and scan evidence.
- Its source tree is `44c8faa2498a1c76c11ece274a0c9d26031fa9cb`.
- The final local image digest is `sha256:ea42ec6172063b0ee06afc3455801af4e0b0cc23785e95beb7f49a1179ecc8eb`.
- The later review head contains documentation, roadmap, runbook, and test-maintenance changes but no replacement runtime evidence.
- A release authority must explicitly select one immutable candidate commit before signing.
- Selecting `d273c9a` may reuse only its matching retained evidence and image digest.
- Selecting a code-bearing successor requires fresh preflight, image, smoke, and scan evidence.
- A branch name, mutable tag, working tree, or abbreviated digest cannot identify an approved candidate alone.
- Signing, promotion, publication, staging, and deployment remain separate decisions.
