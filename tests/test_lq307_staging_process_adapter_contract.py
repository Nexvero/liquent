from pathlib import Path


ROOT = Path(__file__).parents[1]
DOCUMENT = ROOT / "docs/lq-307-owner-controlled-staging-process-adapter-contract.md"


def _contract() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


def test_contract_requires_explicit_inputs_and_closed_environment() -> None:
    contract = _contract()
    for required in (
        "Compose-Binary", "absoluten Pfaden", "owner-only Runtime-",
        "monotone Clock", "allowlistete Umgebung", "werden nicht", "geerbt",
        "Arbeitsverzeichnis", "keine zusätzlichen caller-gelieferten",
    ):
        assert required in contract


def test_contract_forbids_shell_and_unbounded_process_output() -> None:
    contract = _contract()
    for required in (
        "unveränderliche Argumentlisten", "`shell=True`", "Commandsubstitution",
        "stdin ist geschlossen", "getrennte begrenzte Bytekanäle",
        "feste Timeoutpolicy", "notwendiger harter Kill ergibt `unavailable`",
    ):
        assert required in contract


def test_contract_maps_exact_phases_without_hidden_prerequisites() -> None:
    contract = _contract()
    for required in (
        "exakt die 29", "totale geschlossene Abbildung", "Service-Allowlist",
        "keine Phase implizit", "unbekannter Phasenname", "genau eine Testpermission",
        "genau einen Worker",
    ):
        assert required in contract


def test_contract_reduces_output_and_writes_only_neutral_evidence() -> None:
    contract = _contract()
    for required in (
        "Rohoutput wird nie persistiert", "maximaler Bytegröße",
        "Unbekannte Schlüssel", "eindeutiger Invariantenbruch ergibt `failed`",
        "Technische", "Mehrdeutigkeit ergibt `unavailable`", "SHA-256-Read-back",
        "Digest exakt `None`",
    ):
        assert required in contract


def test_contract_bounds_signals_ownership_and_external_effects() -> None:
    contract = _contract()
    for required in (
        "genau ein SIGTERM", "kein zweites", "SIGKILL niemals erfolgreich",
        "extern besessen", "kein automatisches `compose down`",
        "keine CLI", "keine realen Unterprozesse", "LQ-308",
    ):
        assert required in contract
