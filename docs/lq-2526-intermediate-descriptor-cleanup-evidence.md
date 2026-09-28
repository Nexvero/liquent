# LQ-2526 Intermediate descriptor-cleanup evidence

- Focused evidence injects failure after the first descriptor has been closed.
- The remaining workspace descriptor still receives exactly one close attempt.
- The caller observes only the fixed controlled rejection boundary.
- Existing successful cleanup evidence continues to show two distinct closes.
- Full release-preflight and complete project regressions remain required.
- Production readiness remains false; publication and deployment stay forbidden.
