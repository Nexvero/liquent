import json
from pathlib import Path

import pytest

import liquent_platform.operators.release_publication as operator
from liquent_platform.identity.release_publication import (
    ReleasePublicationArtifactBinding,
    ReleasePublicationHandoffId,
    ReleasePublicationWorkResult,
    ReleasePublicationWorkResultKind,
)


def _private(path: Path, value: str) -> Path:
    path.write_text(value)
    path.chmod(0o600)
    return path


def _json(path: Path, value: dict) -> Path:
    return _private(
        path, json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    )


def _work(tmp_path: Path, **changes) -> Path:
    value = {
        "execution_id": "execution-lq275",
        "handoff_id": "handoff-lq275",
        "publisher_authority_id": "publisher-lq275",
        "channel_id": "channel-lq275",
        "expected_channel_revision": "revision-lq275",
    }
    value.update(changes)
    return _json(tmp_path / "work.json", value)


def test_closed_work_request_is_private_typed_and_repr_free(tmp_path: Path):
    result = operator.load_work_request(_work(tmp_path))
    assert result.execution_id.value == "execution-lq275"
    assert result.handoff_id.value == "handoff-lq275"
    assert repr(result) == "ReleasePublicationWorkRequest()"


@pytest.mark.parametrize(
    "mutation",
    [
        {"phase": "create"},
        {"attempt_id": "caller-attempt"},
        {"allow": True},
        {"origin": "https://other.example"},
    ],
)
def test_work_request_rejects_every_open_control(tmp_path: Path, mutation):
    with pytest.raises(operator.ReleasePublicationOperatorInputRejected):
        operator.load_work_request(_work(tmp_path, **mutation))


def test_noncanonical_duplicate_and_unsafe_files_fail_closed(tmp_path: Path):
    noncanonical = _private(
        tmp_path / "noncanonical.json",
        '{"execution_id":"x", "handoff_id":"h"}\n',
    )
    with pytest.raises(operator.ReleasePublicationOperatorInputRejected):
        operator.load_work_request(noncanonical)
    duplicate = _private(
        tmp_path / "duplicate.json",
        '{"channel_id":"c","execution_id":"e",'
        '"expected_channel_revision":"r","handoff_id":"h",'
        '"handoff_id":"other","publisher_authority_id":"p"}\n',
    )
    with pytest.raises(operator.ReleasePublicationOperatorInputRejected):
        operator.load_work_request(duplicate)
    unsafe = _work(tmp_path)
    unsafe.chmod(0o640)
    with pytest.raises(operator.ReleasePublicationOperatorUnavailable):
        operator.load_work_request(unsafe)


def test_artifact_source_requires_absolute_paths_and_exact_signature_name(
    tmp_path: Path,
):
    bundle = tmp_path / "bundle.tar.gz"
    signature = tmp_path / "bundle.tar.gz.sshsig"
    evidence = tmp_path / "promotion.json"
    configuration = operator.load_artifact_source(_json(
        tmp_path / "artifacts.json",
        {
            "handoff_id": "handoff-lq275",
            "bundle_path": str(bundle),
            "signature_path": str(signature),
            "promotion_evidence_path": str(evidence),
        },
    ))
    assert configuration.handoff_id.value == "handoff-lq275"
    assert "bundle" not in repr(configuration)
    with pytest.raises(operator.ReleasePublicationOperatorInputRejected):
        operator.load_artifact_source(_json(
            tmp_path / "relative.json",
            {
                "handoff_id": "handoff-lq275",
                "bundle_path": "relative.tar.gz",
                "signature_path": "relative.tar.gz.sshsig",
                "promotion_evidence_path": "promotion.json",
            },
        ))


def test_single_handoff_source_accepts_only_system_binding(tmp_path: Path):
    bundle = tmp_path / "bundle.tar.gz"
    signature = tmp_path / "bundle.tar.gz.sshsig"
    evidence = tmp_path / "promotion.json"
    bundle.write_bytes(b"bundle")
    signature.write_bytes(b"signature")
    evidence.write_bytes(b"evidence")
    source = operator.SingleHandoffReleasePublicationArtifactSource(
        operator.ReleasePublicationArtifactSourceConfiguration(
            ReleasePublicationHandoffId("handoff-lq275"),
            bundle,
            signature,
            evidence,
        )
    )
    binding = ReleasePublicationArtifactBinding(
        ReleasePublicationHandoffId("handoff-lq275"), "a", "b", "c"
    )
    assert source.load_artifacts(binding).bundle == b"bundle"
    with pytest.raises(operator.ReleasePublicationOperatorUnavailable):
        source.load_artifacts(ReleasePublicationArtifactBinding(
            ReleasePublicationHandoffId("other"), "a", "b", "c"
        ))


def test_provider_configuration_is_closed_and_bounded(tmp_path: Path):
    credential = tmp_path / "credential"
    value = {
        "origin": "https://packages.example",
        "target_name": "stable",
        "credential_path": str(credential),
        "connect_timeout_seconds": 1,
        "read_timeout_seconds": 2,
        "total_timeout_seconds": 3,
        "request_max_bytes": 4096,
        "response_max_bytes": 2048,
    }
    result = operator.load_provider_configuration(
        _json(tmp_path / "provider.json", value)
    )
    assert result.policy.total_timeout.total_seconds() == 3
    assert "packages.example" not in repr(result)
    value["retry_count"] = 3
    with pytest.raises(operator.ReleasePublicationOperatorInputRejected):
        operator.load_provider_configuration(
            _json(tmp_path / "provider-open.json", value)
        )
    value.pop("retry_count")
    value["origin"] = "http://packages.example"
    with pytest.raises(operator.ReleasePublicationOperatorInputRejected):
        operator.load_provider_configuration(
            _json(tmp_path / "provider-insecure.json", value)
        )


@pytest.mark.parametrize(
    ("kind", "name", "status"),
    [
        (ReleasePublicationWorkResultKind.PUBLISHED, "published", 0),
        (
            ReleasePublicationWorkResultKind.PUBLISHED_REASSESSMENT_REQUIRED,
            "published_reassessment_required",
            6,
        ),
        (ReleasePublicationWorkResultKind.NOT_PUBLISHED, "not_published", 7),
        (
            ReleasePublicationWorkResultKind.PUBLICATION_CONFLICT,
            "publication_conflict",
            8,
        ),
        (
            ReleasePublicationWorkResultKind.PENDING_RECONCILIATION,
            "pending_reconciliation",
            9,
        ),
        (ReleasePublicationWorkResultKind.NOT_ACTIONABLE, "not_actionable", 5),
    ],
)
def test_main_emits_only_canonical_outcome(
    tmp_path: Path, monkeypatch, capsys, kind, name, status
):
    monkeypatch.setattr(
        operator,
        "run_operator",
        lambda **_: ReleasePublicationWorkResult(kind),
    )
    arguments = []
    for option in (
        "--database-url-file", "--request", "--artifact-source", "--provider",
        "--executor-id-file", "--promotion-verifier-id-file",
    ):
        arguments.extend((option, str(tmp_path / option[2:])))
    assert operator.main(arguments) == status
    captured = capsys.readouterr()
    assert captured.out == f'{{"outcome":"{name}"}}\n'
    assert captured.err == ""


def test_main_separates_input_and_technical_failures(
    tmp_path: Path, monkeypatch, capsys
):
    arguments = []
    for option in (
        "--database-url-file", "--request", "--artifact-source", "--provider",
        "--executor-id-file", "--promotion-verifier-id-file",
    ):
        arguments.extend((option, str(tmp_path / option[2:])))
    monkeypatch.setattr(
        operator,
        "run_operator",
        lambda **_: (_ for _ in ()).throw(
            operator.ReleasePublicationOperatorInputRejected()
        ),
    )
    with pytest.raises(SystemExit) as rejected:
        operator.main(arguments)
    assert rejected.value.code == 2
    assert capsys.readouterr().err == (
        '{"error":"release_publication_operator_input_rejected"}\n'
    )
    monkeypatch.setattr(
        operator,
        "run_operator",
        lambda **_: (_ for _ in ()).throw(RuntimeError("private-detail")),
    )
    with pytest.raises(SystemExit) as unavailable:
        operator.main(arguments)
    assert unavailable.value.code == 4
    captured = capsys.readouterr()
    assert captured.err == '{"error":"release_publication_operator_unavailable"}\n'
    assert "private-detail" not in captured.err
