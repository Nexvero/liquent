from pathlib import Path


ROOT = Path(__file__).parents[1]
DOCUMENT = ROOT / "docs/lq-313-controlled-runtime-inspection-contract.md"


def _contract() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


def test_contract_bounds_three_runtime_phases_without_product_mutation() -> None:
    contract = _contract()
    mappings = {
        "`entrypoint`": "`entrypoint_present`",
        "`input_ownership`": "`inputs_owner_only`",
        "`data_read_only`": "`data_read_only`",
    }
    for phase, fact in mappings.items():
        assert phase in contract and fact in contract
    for required in (
        "keine Produkt-", "Datenbank-", "Researchjob-", "Artifact-",
        "kurzlebiger Containerstart ist eine Dockerzustandsänderung",
    ):
        assert required in contract


def test_contract_hardens_ephemeral_container_and_excludes_secrets() -> None:
    contract = _contract()
    for required in (
        "`--rm`", "read-only Rootfilesystem", "`no-new-privileges`",
        "Drop aller Linux-Capabilities", "Netzwerkmodus `none`", "keine Devices",
        "geschlossene stdin", "`/tmp`-tmpfs", "CPU-, Memory-, PID-",
        "Kein Secret wird gemountet", "`/run/secrets/database_url`",
    ):
        assert required in contract


def test_contract_uses_fixed_inspector_without_shell_or_worker_start() -> None:
    contract = _contract()
    for required in (
        "`liquent-runtime-inspect`", "absoluten", "kein `python -c`",
        "kein PATH-Lookup", "keine Shell", "keine caller-gelieferten Prüfprogramme",
        "startet den Worker nicht", "Releasemanifest gebundene",
    ):
        assert required in contract


def test_entrypoint_and_input_ownership_are_descriptor_bound() -> None:
    contract = _contract()
    for required in (
        "`liquent-research-worker` genau einmal", "research_worker:main",
        "reguläre Datei", "group/world-writable", "No-follow-Semantik",
        "UID 10001", "Linkcount eins", "0400 oder 0600", "Dateiinhalte werden nicht gelesen",
    ):
        assert required in contract


def test_data_read_only_uses_observation_not_probe_write() -> None:
    contract = _contract()
    for required in (
        "Mountinfo", "read-only", "nicht", "schreibbar", "keinen Create-",
        "Open-for-write", "Rename-", "Link-", "Unlink-", "Probe-Write-Versuch",
        "nicht durch", "absichtlich fehlschlagende Mutation",
    ):
        assert required in contract


def test_unknown_outcome_never_retries_or_cleans_up() -> None:
    contract = _contract()
    for required in (
        "Unknown Outcome", "erforderlicher SIGKILL", "keinen zweiten Inspectioncontainer",
        "keine automatische Bereinigung", "Incident-/Recovery-", "Bestand",
        "kein `compose down`", "LQ-314", "LQ-315",
    ):
        assert required in contract
