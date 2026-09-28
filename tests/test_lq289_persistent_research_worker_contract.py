from pathlib import Path


ROOT = Path(__file__).parents[1]
DOCUMENT = ROOT / "docs/lq-289-persistent-research-worker-foundation-contract.md"


def _contract() -> str:
    return DOCUMENT.read_text()


def test_audit_identifies_in_memory_visibility_and_restart_blockers():
    contract = _contract()
    for required in (
        "InMemoryResearchJobs", "weder zwischen", "Prozessneustart",
        "keine persistente Queue", "Mehrprozess-Claim",
        "Restart-Recovery",
    ):
        assert required in contract


def test_contract_requires_stable_closed_authorized_persistent_jobs():
    contract = _contract()
    for required in (
        "stabile, nicht wiederverwendbare `JobId`", "Workspace-ID",
        "User-ID als Actorreferenz", "Experiment-Snapshot",
        "Session-ID", "CSRF-Token", "Allow-Entscheidung",
        "Ohne Commit", "research:write",
    ):
        assert required in contract


def test_contract_requires_atomic_claim_lease_heartbeat_and_recovery():
    contract = _contract()
    for required in (
        "atomar claimen", "Claim-/Lease-Identität", "nicht gleichzeitig",
        "Heartbeat", "eigene aktuelle Lease", "abgelaufene Lease beweist nicht",
        "nicht blind", "unabhängigen Verbindungen",
    ):
        assert required in contract


def test_contract_closes_runner_result_and_artifact_boundaries():
    contract = _contract()
    for required in (
        "keine Python-Importpfade", "Shellbefehle", "Pickles",
        "ArtifactStore", "kein `succeeded` ohne vollständige Results",
        "Artifactwrite ohne bestätigten Jobabschluss", "detailarmen terminalen",
    ):
        assert required in contract


def test_contract_bounds_loop_concurrency_readiness_and_shutdown():
    contract = _contract()
    for required in (
        "Jobkonkurrenz auf genau eins", "keine interne Thread-",
        "leerer Queuezustand ist gesund", "Busy Loop", "SIGTERM",
        "keinen zweiten", "setzt RUNNING nicht blind auf READY",
    ):
        assert required in contract


def test_contract_separates_research_worker_from_publication_and_defers_implementation():
    contract = _contract()
    for required in (
        "Trennung vom Publication-Worker", "darf diesen Command",
        "weder importieren noch aufrufen", "keine Tabelle", "keinen Job",
        "Stack bleibt nicht runnable", "LQ-290",
    ):
        assert required in contract
