from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_current_job_file_is_private_to_host_owner() -> None:
    adapter = _read(
        "src/liquent_platform/transport/manifest_handoff_supervisor_job_document.py"
    )

    assert "0o600, dir_fd=descriptor" in adapter
    assert "facts.st_uid != os.geteuid()" in adapter
    assert "stat.S_IMODE(facts.st_mode) != 0o600" in adapter
    assert "fchown" not in adapter and "chown" not in adapter


def test_current_container_mount_now_supplies_separate_reader_contract() -> None:
    client = _read("src/liquent_platform/transport/local_docker_engine_http_client.py")

    assert '"User": self._user' in client
    assert ':/run/liquent/control:rw"' in client
    assert "reader_gid" in client
    assert ':/run/liquent/launch/launch-binding.json:ro"' in client
    assert 'base / "control-artifacts"' in client
    assert ":/run/liquent/job-binding.json:ro" not in client


def test_current_engine_labels_have_no_independent_document_anchor() -> None:
    engine = _read(
        "src/liquent_platform/transport/manifest_handoff_supervisor_docker_engine.py"
    )
    client = _read("src/liquent_platform/transport/local_docker_engine_http_client.py")

    for label in ("creation", "handle", "control", "profile"):
        assert f"liquent.supervisor.{label}" in engine
        assert f"liquent.supervisor.{label}" in client
    assert "job-document" not in engine
    assert "job-document" not in client


def test_current_document_contains_post_create_runtime_identity() -> None:
    domain = _read(
        "src/liquent_platform/identity/manifest_handoff_supervisor_job_document.py"
    )
    prepare = _read(
        "src/liquent_platform/application/manifest_handoff_supervisor_prepare_service.py"
    )

    assert "runtime_container_id: ManifestHandoffSupervisorRuntimeContainerId" in domain
    assert "runtime = self._create_and_bind(command, profile)" in prepare
    assert "job_document" not in prepare


def test_lq603_explicitly_rejects_self_hash_as_anchor() -> None:
    audit = _read("docs/lq-603-wrapper-job-document-loader-implementation-blocker-audit.md")

    for required in (
        "Blocker 1 — Dateizugriff",
        "Blocker 2 — zirkulärer Runtime-Anchor",
        "Warum Selbsthash nicht genügt",
        "separaten read-only Bind-Mount",
        "keinen Wrapperentrypoint und kein Ready",
    ):
        assert required in audit


def test_corrected_launch_contract_is_precreate_and_digest_anchored() -> None:
    contract = _read(
        "docs/lq-604-precreate-digest-bound-wrapper-launch-document-contract.md"
    )

    assert "Es enthält keine Runtime-Container-ID" in contract
    assert "Document-ID" in contract and "SHA-256" in contract
    assert "vor dem ersten Engine-Create" in contract
    assert "Runtimebestand separat" in contract
    assert "keine fachliche Authority" in contract


def test_mount_contract_separates_immutable_and_dynamic_files() -> None:
    contract = _read("docs/lq-605-read-only-wrapper-launch-document-mount-contract.md")

    assert "einzelne Datei read-only" in contract
    assert "einen getrennten" in contract
    assert "begrenzten read-write Control-Mount" in contract
    assert "Numerische UID und GID" in contract
    assert "keinen chmod-, chown-, Remount-" in contract
    assert "Parent publiziert kein stellvertretendes Ready" in contract


def test_decision_keeps_runtime_closed_and_orders_follow_up() -> None:
    decision = _read("docs/lq-606-wrapper-launch-binding-blocker-decision.md")
    roadmap = _read("docs/technical-status-and-roadmap.md")

    assert "Sichere Reihenfolge" in decision
    assert "LQ-607 implementiert" in decision
    for slice_id in range(603, 607):
        assert f"- LQ-{slice_id} " in roadmap
        assert f"docs/lq-{slice_id}-" in roadmap
