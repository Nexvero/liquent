import json
from pathlib import Path

import pytest

from liquent_platform.identity.release_publication import (
    AcceptedReleasePublicationHandoff,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationHandoffId,
)
from liquent_platform.operators import release_publication_handoff as operator
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationHandoffConflict,
)


def _private(path: Path, value: str) -> Path:
    path.write_text(value)
    path.chmod(0o600)
    return path


def _request(tmp_path: Path, **changes) -> Path:
    bundle = _private(tmp_path / "bundle.tar.gz", "bundle")
    signature = _private(tmp_path / "bundle.tar.gz.sshsig", "signature")
    evidence = _private(tmp_path / "promotion.json", "evidence")
    payload = {
        "bundle_path": str(bundle),
        "channel_id": "channel-284",
        "channel_revision_id": "channel-revision-284",
        "decision_id": "decision-284",
        "execution_id": "execution-284",
        "handoff_id": "handoff-284",
        "promotion_evidence_path": str(evidence),
        "publisher_authority_id": "publisher-284",
        "signature_path": str(signature),
    }
    payload.update(changes)
    return _private(
        tmp_path / "request.json",
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
    )


def test_request_is_closed_and_preserves_execution_id(tmp_path):
    request = operator.load_request(_request(tmp_path))
    assert request.execution_id.value == "execution-284"
    assert request.bundle_path.is_absolute()


@pytest.mark.parametrize("changes", [
    {"allow": True},
    {"executor_id": "caller"},
    {"role": "publisher"},
    {"provider_origin": "https://caller.invalid"},
])
def test_request_rejects_open_authority_or_provider_fields(tmp_path, changes):
    with pytest.raises(operator.ReleasePublicationHandoffOperatorInputRejected):
        operator.load_request(_request(tmp_path, **changes))


def test_main_emits_minimal_success_and_neutral_result(tmp_path, monkeypatch, capsys):
    request = operator.load_request(_request(tmp_path))
    accepted = AcceptedReleasePublicationHandoff(
        ReleasePublicationHandoffId("handoff-284"),
        ReleasePublicationDecisionId("decision-284"),
        ReleasePublicationChannelId("channel-284"),
        ReleasePublicationChannelPolicyRevisionId("channel-revision-284"),
    )
    arguments = [
        "--database-url-file", str(tmp_path / "database"),
        "--request", str(tmp_path / "request.json"),
    ]
    monkeypatch.setattr(operator, "run_operator", lambda **_: (request, accepted))
    assert operator.main(arguments) == 0
    assert json.loads(capsys.readouterr().out) == {
        "channel_id": "channel-284",
        "channel_revision_id": "channel-revision-284",
        "decision_id": "decision-284",
        "execution_id": "execution-284",
        "handoff_id": "handoff-284",
        "outcome": "accepted",
    }
    monkeypatch.setattr(operator, "run_operator", lambda **_: (request, None))
    assert operator.main(arguments) == 5
    assert capsys.readouterr().out == '{"outcome":"not_accepted"}\n'


def test_main_separates_input_conflict_and_unavailability(tmp_path, monkeypatch, capsys):
    arguments = [
        "--database-url-file", str(tmp_path / "database"),
        "--request", str(tmp_path / "request"),
    ]
    cases = (
        (operator.ReleasePublicationHandoffOperatorInputRejected(), 2,
         "release_publication_handoff_operator_input_rejected"),
        (ReleasePublicationHandoffConflict(), 3,
         "release_publication_handoff_operator_conflict"),
        (operator.ReleasePublicationHandoffOperatorUnavailable(), 4,
         "release_publication_handoff_operator_unavailable"),
    )
    for error, status, code in cases:
        monkeypatch.setattr(
            operator, "run_operator",
            lambda error=error, **_: (_ for _ in ()).throw(error),
        )
        with pytest.raises(SystemExit) as caught:
            operator.main(arguments)
        assert caught.value.code == status
        assert json.loads(capsys.readouterr().err) == {"error": code}
