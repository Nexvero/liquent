# LQ-2525 Intermediate descriptor-cleanup boundedness

- Cleanup iterates only descriptors opened from the fixed expected-name mapping.
- At most four retained children and one workspace descriptor are involved.
- No filesystem scan, recursive deletion, or caller-selected target is performed.
- Each attempted close is independent of receipt and phase callback behavior.
- Failure records only a local boolean until all cleanup attempts finish.
- The verifier retains no descriptor state between invocations.
