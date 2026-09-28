# LQ-1812 Closed joint engine API accepted evidence handoff

- Valid evidence is unpacked only after exact shape validation.
- Closed result stores the source and marker observations.
- Construction rederives expected marker acceptance.
- Success checks consume only that closed result.
- No raw tuple survives beyond operation formation.
- Failure paths expose no evidence detail.
- Public successful output remains empty.
