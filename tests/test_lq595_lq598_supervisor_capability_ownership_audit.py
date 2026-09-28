from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_current_parent_publishes_ready_instead_of_observing_child_ready() -> None:
    prepare = _read(
        "src/liquent_platform/application/manifest_handoff_supervisor_prepare_service.py"
    )

    assert "self._wrapper.publish_ready" in prepare
    assert "self._artifacts.record_ready" in prepare


def test_current_parent_publishes_consumed_then_calls_second_executor() -> None:
    release = _read(
        "src/liquent_platform/application/manifest_handoff_supervisor_release_service.py"
    )

    assert "self._wrapper.publish_consumed" in release
    main_flow = release[release.index("def _release("):release.index("def _publish_release(")]
    running = main_flow.index("journal = record_running(")
    execute = main_flow.index("executed = execute(execution)")
    assert running < execute


def test_compatibility_executor_delegates_to_old_release_ports() -> None:
    executor = _read(
        "src/liquent_platform/application/manifest_handoff_supervisor_capability_executor.py"
    )

    assert "self._writer.release_writer" in executor
    assert "self._recovery.release_recovery" in executor
    assert "CompletedManifestHandoffWriterProcess" in executor
    assert "CompletedManifestHandoffRecoveryProcess" in executor


def test_lq595_rejects_direct_primitive_implementation_for_production_graph() -> None:
    audit = _read("docs/lq-595-supervisor-capability-double-effect-blocker-audit.md")

    for required in (
        "Die Entscheidung lautet: nein",
        "Verdeckte zweite Wirkung",
        "Ready ist nicht direkt",
        "Consumed ist nicht direkt",
        "LQ-468-Adapter ist jedoch ein Kompatibilitätsadapter",
        "Productiongraph bleibt dennoch geschlossen",
    ):
        assert required in audit


def test_child_wrapper_contract_assigns_each_effect_once() -> None:
    contract = _read("docs/lq-596-child-owned-supervisor-capability-wrapper-contract.md")

    assert "Nur der Kindprozess publiziert sein Ready-Artefakt" in contract
    assert "Der Wrapper publiziert selbst genau ein Consumed-Artefakt" in contract
    assert "ausschließlich der Wrapper genau ein" in contract
    assert "Recoveryprofil ruft ausschließlich den bestehenden read-only Reconciler" in contract
    assert "keinen Retry nach möglicher" in contract
    assert "Dateiwirkung" in contract


def test_parent_contract_is_observation_only_after_release() -> None:
    contract = _read("docs/lq-597-observation-only-supervisor-parent-service-contract.md")

    assert "Er publiziert Ready niemals selbst" in contract
    assert "Consummed-Artefakt" not in contract
    assert "Consumed-Artefakt wird ausschließlich vom Wrapper erzeugt" in contract
    assert "keinen zweiten Writer-/Recovery-Supervisor" in contract
    assert "LQ-468 darf in diesem Productionpfad nicht verdrahtet werden" in contract


def test_decision_keeps_runtime_wiring_closed_and_sets_safe_sequence() -> None:
    decision = _read("docs/lq-598-supervisor-capability-ownership-blocker-decision.md")

    assert "Sichere Implementierungsreihenfolge" in decision
    assert "Settings, Appfactory, Lifespan, Compose, Docker-Socket-Mount" in decision
    assert "LQ-599 definiert das kanonische wrappergebundene Jobdokument" in decision


def test_roadmap_records_complete_four_slice_audit_bundle() -> None:
    roadmap = _read("docs/technical-status-and-roadmap.md")

    for slice_id in range(595, 599):
        assert f"- LQ-{slice_id} " in roadmap
        assert f"docs/lq-{slice_id}-" in roadmap
    assert "nächster Strang LQ-599" in roadmap
