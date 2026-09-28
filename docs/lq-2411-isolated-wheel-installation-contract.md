# LQ-2411 Isolated wheel-installation contract

- Entry-point evidence must come from the verified local wheel alone.
- Package-index access, dependency resolution, bytecode generation, and Pip self-checks
  are outside this installation boundary.
- User configuration and Pip environment variables must not alter installation policy.
- The fixed private installed-wheel directory remains the only installation target.
- This local installation is evidence only and is never a deployment artifact.
