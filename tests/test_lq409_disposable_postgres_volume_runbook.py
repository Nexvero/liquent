from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNBOOK = ROOT / "operations/runbooks/disposable-postgres-volume-disposition-deletion.md"
PYPROJECT = ROOT / "pyproject.toml"
COMMANDS = (
    "liquent-disposable-postgres-volume-disposition",
    "liquent-disposable-postgres-volume-deletion-preflight",
    "liquent-disposable-postgres-volume-delete",
    "liquent-disposable-postgres-volume-delete-reconcile",
    "liquent-disposable-postgres-volume-delete-finalize",
    "liquent-disposable-postgres-volume-delete-continue",
    "liquent-disposable-postgres-volume-delete-continue-reconcile",
    "liquent-disposable-postgres-volume-delete-continue-finalize",
    "liquent-disposable-postgres-volume-delete-terminal-handoff",
)


def test_runbook_has_all_installed_commands_in_authority_order() -> None:
    text = RUNBOOK.read_text()
    project = PYPROJECT.read_text()
    positions = [text.index(f"`{command}`") for command in COMMANDS]
    assert positions == sorted(positions)
    assert all(f"{command} =" in project for command in COMMANDS)
    assert "not permission to invoke\nall 9 commands" in text


def test_runbook_closes_authority_unknown_outcome_and_retry_routes() -> None:
    text = RUNBOOK.read_text()
    required = (
        "umask 077",
        "Authorization-material handoff",
        "Do not rerun this mutating command after unknown outcome",
        "After a possible Stage C effect, route only to Stage D",
        "After a possible Stage\nF effect, route only to Stage G",
        "An evidence retry repeats only the exact",
        "There is no third remove and no second continuation",
        "Exit code `2` never means `not_found` or success",
    )
    assert all(item in text for item in required)


def test_runbook_requires_incident_retention_and_terminal_evidence() -> None:
    text = RUNBOOK.read_text()
    required = (
        "Incident stop",
        "Evidence retention and private inventory",
        "Successful local closeout",
        "volume_deletion_finalized",
        "the exact subordinate claim is absent",
        "the exact original deletion claim is absent",
        "Retention continues after claim release",
        "Never reuse an ID",
    )
    assert all(item in text for item in required)


def test_runbook_forbids_automation_shortcuts_and_global_disposal_claim() -> None:
    text = RUNBOOK.read_text()
    required = (
        "not a script, service, scheduler, CI job",
        "Never use `docker compose down`, `--volumes`, force, prune, mount, export",
        "manual `docker volume rm`",
        "at most two exact remove attempts",
        "Claim absence or local volume absence alone is never successful closeout",
        "Never report “all data disposed”, “fully deleted”",
    )
    assert all(item in text for item in required)
