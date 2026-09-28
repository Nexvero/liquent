from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNBOOK = ROOT / "operations/runbooks/disposable-postgres-runtime-cleanup.md"
PYPROJECT = ROOT / "pyproject.toml"
COMMANDS = (
    "liquent-disposable-postgres-cleanup-preflight",
    "liquent-disposable-postgres-runtime-cleanup",
    "liquent-disposable-postgres-cleanup-reconcile",
    "liquent-disposable-postgres-cleanup-finalize",
    "liquent-disposable-postgres-cleanup-continue",
    "liquent-disposable-postgres-cleanup-continue-reconcile",
    "liquent-disposable-postgres-cleanup-continue-finalize",
    "liquent-disposable-postgres-cleanup-recontinue",
    "liquent-disposable-postgres-cleanup-recontinue-reconcile",
    "liquent-disposable-postgres-cleanup-recontinue-finalize",
    "liquent-disposable-postgres-cleanup-chain-continue",
    "liquent-disposable-postgres-cleanup-chain-reconcile",
    "liquent-disposable-postgres-cleanup-chain-finalize",
    "liquent-disposable-postgres-cleanup-generation-continue",
    "liquent-disposable-postgres-cleanup-generation-reconcile",
    "liquent-disposable-postgres-cleanup-generation-finalize",
)


def test_runbook_has_installed_commands_in_authority_order() -> None:
    text = RUNBOOK.read_text()
    project = PYPROJECT.read_text()
    positions = [text.index(f"`{command}`") for command in COMMANDS]
    assert positions == sorted(positions)
    assert all(f"{command} =" in project for command in COMMANDS)
    assert "not permission to invoke all\n16 commands" in text


def test_runbook_closes_authorization_routing_and_incident_boundaries() -> None:
    text = RUNBOOK.read_text()
    required = (
        "umask 077",
        "Authorization-material handoff",
        "Unknown outcome routes only",
        "An evidence retry repeats only",
        "Generation 1",
        "Generation 2",
        "Generations 3 through 17",
        "Generation 18",
        "terminal handoff to cleanup finalization",
        "Exit code `2` never means `not_found` or success",
        "Evidence retention and private inventory",
        "runtime_cleanup_finalized",
    )
    assert all(item in text for item in required)
    assert "Do not pass generation files to LQ-343" in text


def test_runbook_forbids_automation_shortcuts_and_volume_disposition() -> None:
    text = RUNBOOK.read_text()
    required = (
        "not a script, service, scheduler, CI job",
        "Never use `docker compose down`, `--volumes`, force, prune",
        "Do not rerun this mutating command",
        "forbid manual Docker mutation, claim deletion, evidence repair",
        "Volume disposition remains separate",
        "never report the disposable environment as fully\ndisposed",
    )
    assert all(item in text for item in required)
