from pathlib import Path


ROOT = Path(__file__).parents[1]
DOCUMENT = ROOT / "docs/lq-310-closed-staging-probe-command-contract.md"


def _contract() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


def test_contract_closes_cli_and_docker_invocation() -> None:
    contract = _contract()
    for required in (
        "`--phase`", "`--docker-executable`", "`--compose-file`",
        "`--authorization-file`", "`--runtime-env-file`", "`--image-env-file`", "`--project-name`",
        "genau einmal", "feste argv-Listen ohne Shell", "beide `--env-file`",
        "Build, Bake", "System-Prune",
    ):
        assert required in contract


def test_contract_defines_exact_neutral_output_and_unavailability() -> None:
    contract = _contract()
    for required in (
        '"schema_version":1', '"facts"', "genau eine kanonische Zeile",
        "stderr", "bleibt leer", "keine weiteren Schlüssel", "Nonzero-Exit",
        "ausschließlich zu", "`unavailable`",
    ):
        assert required in contract


def test_contract_names_every_phase_and_exact_parser_fact() -> None:
    contract = _contract()
    mappings = {
        "image_digest": "digest_matches", "image_revision": "revision_matches",
        "entrypoint": "entrypoint_present", "runtime_identity": "uid_gid_matches",
        "disposable_postgres": "database_isolated", "rollback": "rollback_current",
        "trading_disabled": "trading_disabled", "compose_render": "render_valid",
        "command": "command_exact", "networks": "networks_isolated",
        "mounts": "mounts_bounded", "secret_mount": "secret_owner_only",
        "grace": "grace_bounded", "input_ownership": "inputs_owner_only",
        "data_read_only": "data_read_only",
        "artifact_capabilities": "artifact_capabilities_valid",
        "migration_gate": "migration_gate_succeeded",
        "migration_head": "migration_head_exact", "idle_start": "idle_stable",
        "idle_no_mutation": "idle_mutation_free", "log_redaction": "logs_redacted",
        "authorized_acceptance": "acceptance_authorized",
        "claim_heartbeat": "claim_heartbeat_exact",
        "terminal_outcome": "terminal_outcome_exact",
        "artifact_integrity": "artifact_hash_matches",
        "revocation": "revocation_fail_closed", "idle_sigterm": "idle_stop_clean",
        "running_sigterm": "running_stop_bounded", "no_sigkill": "sigkill_unused",
    }
    assert len(mappings) == 29
    for phase, fact in mappings.items():
        assert f"`{phase}`" in contract
        assert f"`{fact}`" in contract


def test_contract_bounds_mutations_and_forbids_hidden_prerequisites() -> None:
    contract = _contract()
    for required in (
        "dedizierte rungebundene", "genau einmal", "genau einen `research-worker`",
        "bestehende\nauthentifizierte Staging-Control-Plane", "synthetischen Actor",
        "genau ein SIGTERM", "Keine mutierende Phase darf implizit",
        "startet `idle_start` kein Migration-Gate", "`revocation` keinen ersten Job",
    ):
        assert required in contract


def test_contract_preserves_unknown_outcome_secrets_and_external_ownership() -> None:
    contract = _contract()
    for required in (
        "Unknown Outcome", "wiederholt keine Operation", "heuristische Logs",
        "read-only Recovery-/Reconciliation-Slice", "DSNs", "CSRF-Tokens",
        "extern besessen", "kein `compose down`", "keine Probeimplementierung",
        "LQ-311",
    ):
        assert required in contract
