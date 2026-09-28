# LQ-2537 Mid-capture metadata-drift rejection

- Evidence changes child mode immediately after initial namespace measurement.
- The initial returned metadata still represents the prior private state.
- Terminal descriptor and namespace observations see the changed mode.
- Capture rejects rather than returning the otherwise unchanged identity.
- Later intermediate verification cannot adopt or repair this failed state.
- Temporary workspace cleanup remains the only local consequence.
