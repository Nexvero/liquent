from pathlib import Path


ROOT = Path(__file__).parents[1]
DOCUMENT = ROOT / "docs/lq-290-persistent-research-job-claim-and-lease-foundation-contract.md"


def _contract() -> str:
    return DOCUMENT.read_text()


def test_contract_separates_acceptance_job_revision_worker_and_claim_identities():
    contract = _contract()
    for required in (
        "ResearchJobAcceptanceId", "`JobId`", "ResearchJobRevisionId",
        "ResearchWorkerId", "ResearchJobClaimId", "nicht wiederverwendbare",
        "Membership, Permission", "ohne zweite Mutation",
    ):
        assert required in contract


def test_acceptance_is_closed_current_authorized_atomic_and_retry_safe():
    contract = _contract()
    for required in (
        "Actor-User-ID", "ExperimentSnapshot", "research:write",
        "aktuell aus dem", "caller-geliefertes",
            "Ohne Commit", "detailfreier", "keinen Runner aus",
    ):
        assert required in contract


def test_snapshot_and_persistent_states_are_canonical_and_closed():
    contract = _contract()
    for required in (
        "Datasetreferenz und Fingerprint", "Strategy-Version-ID",
        "sortierte Strategy-, Risk- und Cost-Parameter", "Domainvalidierung",
        "Pickles", "`queued`", "`running`", "`invalidated`",
    ):
        assert required in contract


def test_claim_rechecks_authority_is_fifo_atomic_and_postgres_safe():
    contract = _contract()
    for required in (
        "erneut gegen", "nach `invalidated`", "FIFO-Reihenfolge",
        "Job-ID als vollständigem Tie-Breaker", "genau einen `queued` Job",
        "Zwei unabhängige Verbindungen", "genau einer denselben Job",
        "keine Transaktion während der Research-Ausführung",
    ):
        assert required in contract


def test_lease_and_heartbeat_use_server_time_and_reject_stale_claims():
    contract = _contract()
    for required in (
        "serverseitigen", "UTC-Zeitbasis", "Caller liefert weder `now`",
        "Heartbeat bindet exakt", "nicht abgelaufener aktueller Claim",
        "Stale Revision", "falscher Worker", "fremder Claim",
        "keine neue Ablaufzeit",
    ):
        assert required in contract


def test_expired_running_work_is_not_blindly_reclaimed_or_finalized():
    contract = _contract()
    for required in (
        "nicht durch den normalen", "nicht automatisch ausgegeben",
        "spätere Recoveryentscheidung", "stale oder abgelaufener Claim",
        "kein Resultat", "keine Resultsignatur",
    ):
        assert required in contract


def test_lookup_retention_outcomes_and_scope_remain_closed():
    contract = _contract()
    for required in (
        "research:read", "Job-ID allein gewährt keinen Zugriff",
        "Queue-Listen", "nicht gelöscht", "Neutrale Ergebnisse",
        "detailfreie technische", "keine konkrete Klasse", "LQ-291",
        "LQ-292",
    ):
        assert required in contract
