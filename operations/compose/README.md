# Slice-0 Compose contract

This directory is a reviewed deployment contract. LQ-301 wires the installed
`liquent-research-worker` command to its explicit owner-only configuration,
stable worker-ID file, existing database-URL secret, read-only research data,
and writable artifact volume. This closes the static Compose wiring gap; it is
not evidence that a production image, PostgreSQL deployment, dataset, or
external environment is ready.
The package now supplies the `liquent-research-worker` command and Compose
passes every argument required by that command.
The offline Publication operator remains a separate supervised boundary and is
not a substitute for this long-running worker.

The joint supervisor Engine API runtime is isolated in the separately supplied
`compose.supervisor-engine-api.yaml` overlay and is additionally opt-in under
the `supervisor-engine-api` profile. It runs through the explicit Python module
entrypoint, as the fixed release inventory intentionally has no additional
console script. Before enabling the profile, copy all four `engine-api-*.env`
examples outside Git, set mode `0600`, run the read-only deployment preflight,
and provision every host bind path. The service runs as `10001:10002`, receives
only supplemental Docker-socket group `998`, drops every capability, and
publishes no TCP port. Its healthcheck connects only to the private Unix health
socket from the same process identity.

- `compose.yaml` defines roles, resource ceilings, internal connectivity,
  persistent volumes, logging limits, and file-mounted secrets.
- `runtime.env.example` contains non-secret process settings only.
- `research-worker.json.example` is a value-complete template whose paths are
  the fixed container mount targets. Copy it outside Git, review it, and set
  mode `0400` or `0600`; do the same for the one-line stable worker-ID file.
- `images.env.example` documents operator-owned immutable image references.
- Real `runtime.env`, image environment files, and secret files stay on the
  deployment host and outside Git.

No service publishes a host port. The existing edge proxy attaches to
`liquent_public` and remains the only public ingress. Grafana, Prometheus, and
PostgreSQL are internal only.

The worker starts only after the migration gate succeeds, verifies the exact
migration head itself, and receives a 60-second graceful-stop window. SIGTERM
requests a bounded stop; the process does not claim another job afterward.
Operators must provision every required host path before rendering or starting
Compose. Compose does not create identities, datasets, secrets, or config.
Render with `runtime.env` as an explicit Compose environment source so its host
path variables participate in interpolation. The image runtime UID must own the
two mounted files as observed inside the container; otherwise startup fails
closed at the entry point.

Before any staging-readiness claim, execute
`operations/runbooks/research-worker-staging-readiness.md`. Static Compose
validation is not a substitute for its effective in-container ownership,
PostgreSQL, job, artifact, revocation, and SIGTERM evidence.
