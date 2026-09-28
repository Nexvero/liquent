from pathlib import Path


ROOT = Path(__file__).parents[1]
DOCUMENT = ROOT / "docs/lq-286-environment-provider-and-deployment-release-contract.md"


def _contract() -> str:
    return DOCUMENT.read_text()


def test_contract_binds_provider_credential_network_host_and_evidence():
    contract = _contract()
    for required in (
        "HTTPS-Origin", "Package-Namen", "Zielnamen", "Credential-Identität",
        "create-only", "DNS", "TLS", "Egress", "Publication-Host",
        "Prozessaccount", "Operational-Bundle-Identität", "Reviewtermin",
    ):
        assert required in contract


def test_contract_keeps_reviews_and_product_authority_separate():
    contract = _contract()
    for required in (
        "Provider-/Package-Ownership", "Security", "Operations",
        "Release-Verantwortung", "caller-geliefertes `allow`",
        "nicht im Produktmodell kodiert",
    ):
        assert required in contract


def test_contract_requires_fail_closed_provider_semantics_without_real_upload():
    contract = _contract()
    for required in (
        "GET liefert Abwesenheit", "create-only PUT", "erwartete `201`-Schema",
        "Wheel-Hash", "nicht überschrieben", "Unknown Outcome",
        "Production-Testupload", "nicht erlaubt",
    ):
        assert required in contract


def test_contract_separates_publication_deployment_rollback_and_withdrawal():
    contract = _contract()
    for required in (
        "Deployment und Package-Publication bleiben getrennte Entscheidungen",
        "zieht ein bereits veröffentlichtes Package nicht zurück",
        "deployt ein veröffentlichtes Package keine Runtime",
        "Delete, Yank oder Replace ist kein Rollback",
    ):
        assert required in contract


def test_contract_has_no_implementation_or_external_effect_claim():
    contract = _contract()
    for excluded in (
        "entscheidet kein Schema", "Migration", "CLI", "Testupload",
        "DNS-Aufruf", "TLS-Handshake", "Credentialread", "Providerrequest",
        "Push", "Deployment oder Rollback",
    ):
        assert excluded in contract
