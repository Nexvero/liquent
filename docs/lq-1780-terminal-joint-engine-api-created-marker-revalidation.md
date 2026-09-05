# LQ-1780 Terminal joint engine API created marker revalidation

- Final source authority selects the accepted run lookup.
- The accepted-run marker is observed from the fixed root.
- Observation must equal the result's created marker.
- Validation follows final source freshness verification.
- Root identity remains bound across the entire operation.
- Marker drift cannot be hidden by an unchanged inventory value.
- No new timing budget is introduced.
