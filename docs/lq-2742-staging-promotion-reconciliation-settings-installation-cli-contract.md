# LQ-2742: Staging promotion reconciliation settings installation CLI contract

## Decision

LQ-2742 defines a minimal presentation boundary for the LQ-2741 settings
installer. A future command accepts exactly four explicit absolute paths in the
fixed order provider source, provider target, process source and process target.
It supplies no default path and performs exactly one installation attempt.

## Invocation contract

The command accepts exactly four positional arguments. Every argument must be
an absolute, non-root path without parent traversal. Missing, additional,
relative or malformed arguments are invalid invocation and must be rejected
before the installer is called.

Arguments are not read from environment variables, a working-directory
convention or a configuration-discovery path. The command does not create
directories and does not accept flags for replacement, update, cleanup,
rotation, retry or reconciliation execution.

## Observable contract

- `INSTALLED` writes only `installed` followed by one newline to stdout and
  exits zero.
- Neutral `PRESENT` writes only `present` followed by one newline to stderr and
  exits three.
- Technical unavailability writes only `unavailable` followed by one newline
  to stderr and exits one.
- Invalid invocation writes only `invalid_invocation` followed by one newline
  to stderr and exits two.
- Unknown installer outcomes fail closed as technical unavailability.

No source content, endpoint, database URL, supplied path, exception detail,
temporary name or target metadata crosses this boundary. Every invocation
emits exactly one fixed token on exactly one stream.

## Safety boundary

Exit zero means only that this invocation durably published both settings
files. `present` is a neutral refusal: it does not compare existing content,
prove a prior successful paired installation or authorize replacement.

The command transports configuration only. It grants no promotion authority,
does not start reconciliation and does not open a database or provider
connection. It performs no network, schema, migration, deployment or health
operation.

## Deliberate exclusions

LQ-2742 adds no CLI implementation, installed entry point, shell wrapper,
default directory, environment lookup, prompt, secret input, logging, metric,
retry, loop, timer, service, worker, route, cleanup, rollback or deployment
decision. Implementation and packaging remain separate slices.
