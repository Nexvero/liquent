from pathlib import Path


ROOT = Path(__file__).parents[1]
CHECKLIST = ROOT / "operations/runbooks/release-environment-readiness.md"


def _checklist() -> str:
    return CHECKLIST.read_text()


def test_checklist_binds_all_environment_scope_facts():
    checklist = _checklist()
    for required in (
        "Stable readiness decision ID", "Canonical HTTPS origin",
        "Package name exactly `liquent`", "provider target name",
        "credential identity", "Operational Bundle SHA-256",
        "Publication host identity", "process-account identity",
        "`valid_from`", "`review_by`",
    ):
        assert required in checklist


def test_checklist_requires_all_evidence_families_and_hashes():
    checklist = _checklist()
    for required in (
        "Provider and package ownership review", "Credential review",
        "TLS, DNS, and egress review", "Publication host review",
        "Monitoring and incident review", "Deployment separation review",
        "lowercase SHA-256", "matches its recorded lowercase SHA-256",
    ):
        assert required in checklist


def test_checklist_requires_four_matching_independent_attestations():
    checklist = _checklist()
    for reviewer in (
        "Provider/package owner", "Security reviewer", "Operations reviewer",
        "Release reviewer",
    ):
        assert reviewer in checklist
    assert "same final evidence-set digest" in checklist
    assert "not application roles" in checklist


def test_checklist_is_offline_secret_free_and_non_activating():
    checklist = _checklist()
    for forbidden in (
        "does not contact DNS", "Production test upload for this checklist",
        "does not resolve a hostname or open a socket",
        "does not start that invocation", "Never record the secret",
    ):
        assert forbidden in checklist


def test_checklist_has_detail_free_fail_closed_outcomes_and_revalidation():
    checklist = _checklist()
    for outcome in ("`approved`", "`rejected`", "`expired`", "`revoked`", "`unavailable`"):
        assert outcome in checklist
    assert "Do not disclose which credential" in checklist
    assert "Revalidate immediately before a real operator start" in checklist
    assert "fails closed" in checklist
