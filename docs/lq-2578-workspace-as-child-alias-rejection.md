# LQ-2578 Workspace-as-child alias rejection

- A fixed child name cannot make the workspace identity a valid child fact.
- Evidence maps `artifacts` directly to the actual workspace identity.
- The tuple is structurally valid but relationally incoherent.
- Verification rejects without opening the workspace descriptor.
- No synthetic replacement identity or child lookup is attempted.
- The supplied alias is not adopted into any controller state.
