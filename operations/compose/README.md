# Slice-0 Compose contract

This directory is a reviewed deployment contract, not yet a runnable release.
LQ-058 must supply the control-plane and worker entry points before any start.

- `compose.yaml` defines roles, resource ceilings, internal connectivity,
  persistent volumes, logging limits, and file-mounted secrets.
- `runtime.env.example` contains non-secret process settings only.
- `images.env.example` documents operator-owned immutable image references.
- Real `runtime.env`, image environment files, and secret files stay on the
  deployment host and outside Git.

No service publishes a host port. The existing edge proxy attaches to
`liquent_public` and remains the only public ingress. Grafana, Prometheus, and
PostgreSQL are internal only.
