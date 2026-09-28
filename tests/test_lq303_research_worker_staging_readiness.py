from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNBOOK = ROOT / "operations/runbooks/research-worker-staging-readiness.md"
COMPOSE = ROOT / "operations/compose/compose.yaml"
DOCUMENT = ROOT / "docs/lq-303-research-worker-staging-readiness-audit.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_runbook_binds_one_immutable_staging_run() -> None:
    runbook = _text(RUNBOOK)
    for required in (
        "opaque run ID", "repository revision", "application image digest",
        "Compose file SHA-256", "expected migration head", "same run and digest",
        "repository@sha256:<64 lowercase hex>",
    ):
        assert required in runbook


def test_runbook_requires_render_and_effective_runtime_evidence() -> None:
    runbook = _text(RUNBOOK)
    for required in (
        "explicit real `runtime.env`", "no attachment to `liquent_public`",
        "stop_grace_period: 60s", "UID `10001`", "mode `0400` or `0600`",
        "only in-container evidence", "exact expected Alembic head",
    ):
        assert required in runbook
    compose = _text(COMPOSE)
    assert 'uid: "10001"' in compose and "mode: 0400" in compose


def test_runbook_covers_job_revocation_artifact_and_sigterm() -> None:
    runbook = _text(RUNBOOK)
    for required in (
        "authenticated", "CSRF-protected", "initial heartbeat",
        "immutable artifact bytes", "Revoke `research:write`",
        "fail-closed invalidation", "send exactly one SIGTERM",
        "shutdown within 60 seconds", "never duplicate terminal outcomes",
    ):
        assert required in runbook


def test_audit_does_not_claim_missing_external_evidence() -> None:
    document = _text(DOCUMENT)
    for required in (
        "nicht ausgeführt", "nicht freigegeben", "kein Docker-Daemon",
        "keine Staging-PostgreSQL-URL", "`unavailable`", "LQ-304",
    ):
        assert required in document
    for forbidden in ("Staging ist produktionsbereit", "Production ist freigegeben"):
        assert forbidden not in document
