# LQ-2540 Ordered preflight descriptor-close sequence

- Callers provide child descriptors before their containing workspace descriptor.
- The helper preserves that order without sorting or deduplication.
- Capture supplies its one child followed by its workspace anchor.
- Intermediate verification supplies all retained children then the workspace.
- Missing optional descriptors are excluded before cleanup begins.
- No descriptor value is accepted from an external request.
