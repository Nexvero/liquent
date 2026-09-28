from pathlib import Path


ROOT=Path(__file__).parents[1]
CREATION=ROOT/"src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_clearance_creation.py"
LOOKUP=ROOT/"src/liquent_platform/persistence/manifest_handoff_supervisor_control_directory_cleanup_clearance.py"
CLAIM=ROOT/"src/liquent_platform/persistence/manifest_handoff_supervisor_control_directory_cleanup_write_claim.py"


def test_creation_queries_closed_active_policy_inside_facts() -> None:
    text=CREATION.read_text(encoding="utf-8")
    assert "mh_supervisor_cleanup_retention_policy_active" in text
    assert "mh_supervisor_cleanup_retention_policy_revisions" in text
    facts=text[text.index("def _facts"):text.index("def _active_foundations")]
    assert "active_policy = self._one(connection, _ACTIVE_POLICY" in facts
    assert "active_policy.revision_id != _encode(decision.policy_revision_id)" in facts


def test_policy_check_follows_eligible_decision_and_precedes_clearance_result() -> None:
    text=CREATION.read_text(encoding="utf-8")
    facts=text[text.index("def _facts"):text.index("def _active_foundations")]
    assert facts.index("CleanupDisposition.ELIGIBLE") < facts.index("active_policy =")
    assert facts.index("active_policy =") < facts.index("return retired, scope")


def test_creation_postgres_lock_serializes_policy_pointer() -> None:
    text=CREATION.read_text(encoding="utf-8")
    lock=text[text.index("LOCK TABLE"):]
    assert "mh_supervisor_cleanup_retention_policy_revisions" in lock
    assert "mh_supervisor_cleanup_retention_policy_active" in lock
    assert "IN SHARE ROW EXCLUSIVE MODE" in lock


def test_clearance_retry_and_write_claim_reuse_same_policy_bound_facts() -> None:
    creation=CREATION.read_text(encoding="utf-8")
    claim=CLAIM.read_text(encoding="utf-8")
    retry=creation[creation.index("def _retry"):creation.index("def _facts")]
    assert "facts = self._facts" in retry
    assert "self._clearances._facts(" in claim


def test_read_only_clearance_lookup_revalidates_active_policy() -> None:
    text=LOOKUP.read_text(encoding="utf-8")
    section=text[text.index("def resolve_control_directory_cleanup_clearance"):text.index("def _journal")]
    assert "active_policy = self._read" in section
    assert "active_policy.revision_id != _encode(decision.policy_revision_id)" in section
    assert "ManifestHandoffSupervisorControlDirectoryCleanupConflict()" in section


def test_no_fallback_or_policy_mutation_exists() -> None:
    combined=CREATION.read_text(encoding="utf-8")+LOOKUP.read_text(encoding="utf-8")
    for forbidden in ("INSERT INTO mh_supervisor_cleanup_retention_policy",
                      "UPDATE mh_supervisor_cleanup_retention_policy",
                      "minimum_retention_seconds", "default_policy"):
        assert forbidden not in combined


def test_roadmap_records_lq541_and_lq542() -> None:
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-541 active retention policy-bound cleanup clearance:" in roadmap
    assert "lq-541-active-retention-policy-bound-cleanup-clearance.md" in roadmap
    assert "nächster Slice LQ-542" in roadmap
