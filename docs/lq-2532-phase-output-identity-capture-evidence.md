# LQ-2532 Phase-output identity-capture evidence

- Focused evidence replaces a private output after its descriptor is opened.
- Namespace lookup observes the replacement while the old object remains held.
- Identity disagreement is rejected and no captured identity is returned.
- Existing intermediate map, cleanup, phase, receipt, and publication tests remain.
- Complete project regression and diff hygiene are required for handoff.
- Production readiness remains false; publication and deployment stay forbidden.
