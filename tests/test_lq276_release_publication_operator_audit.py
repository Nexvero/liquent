import json
from pathlib import Path

import httpx2
from sqlalchemy import Engine, text

import liquent_platform.operators.release_publication as operator
from liquent_platform.transport.package_index_composition import (
    compose_package_index_publication,
)
from test_release_publication_artifacts import ready
from test_release_promotion_verifier import signed_candidate


def _private(path: Path, value: str) -> Path:
    path.write_text(value)
    path.chmod(0o600)
    return path


def _json(path: Path, value: dict[str, object]) -> Path:
    return _private(
        path, json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    )


def audit_operator_publishes_once(
    *,
    engine: Engine,
    database_url: str,
    candidate: dict[str, object],
    evidence_path: Path,
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT execution.handoff_id,execution.publisher_authority_id,"
            " execution.channel_id,execution.channel_revision_id,"
            " handoff.wheel_sha256"
            " FROM release_publication_executions execution"
            " JOIN release_publication_handoffs handoff"
            " ON handoff.handoff_id=execution.handoff_id"
        )).one()
    handoff, publisher, channel, revision = (
        bytes(value).decode() for value in row[:4]
    )
    evidence = json.loads(evidence_path.read_text())
    calls: list[str] = []
    clients: list[httpx2.Client] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.method)
        assert request.headers["authorization"] == "Bearer audit-token"
        if request.method == "GET" and "PUT" not in calls:
            return httpx2.Response(404, content=iter([b""]))
        if request.method == "PUT":
            return httpx2.Response(
                201,
                headers={"content-type": "application/json"},
                content=iter([b'{"provider_request_id":"request-lq276"}']),
            )
        body = json.dumps({
            "canonical_artifact_id": "artifact-lq276",
            "provider_revision": "provider-revision-lq276",
            "package_name": "liquent",
            "package_version": "1.2.3",
            "wheel_sha256": row.wheel_sha256,
            "visible": True,
        }).encode()
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=iter([body]),
        )

    def controlled_provider(**arguments):
        def factory(**client_arguments):
            client = httpx2.Client(
                transport=httpx2.MockTransport(handler), **client_arguments
            )
            clients.append(client)
            return client

        return compose_package_index_publication(
            **arguments, client_factory=factory
        )

    monkeypatch.setattr(
        operator, "compose_package_index_publication", controlled_provider
    )
    credential = _private(tmp_path / "credential", "audit-token\n")
    database = _private(tmp_path / "database-url", database_url + "\n")
    request = _json(tmp_path / "work.json", {
        "execution_id": "execution-255",
        "handoff_id": handoff,
        "publisher_authority_id": publisher,
        "channel_id": channel,
        "expected_channel_revision": revision,
    })
    artifacts = _json(tmp_path / "artifacts.json", {
        "handoff_id": handoff,
        "bundle_path": str(candidate["bundle"]),
        "signature_path": str(candidate["signature"]),
        "promotion_evidence_path": str(evidence_path),
    })
    provider = _json(tmp_path / "provider.json", {
        "origin": "https://packages.example",
        "target_name": "stable",
        "credential_path": str(credential),
        "connect_timeout_seconds": 1,
        "read_timeout_seconds": 1,
        "total_timeout_seconds": 2,
        "request_max_bytes": 16 * 1024 * 1024,
        "response_max_bytes": 4096,
    })
    executor = _private(tmp_path / "executor-id", "executor-255\n")
    verifier = _private(
        tmp_path / "verifier-id", str(evidence["verification_identity"]) + "\n"
    )

    status = operator.main([
        "--database-url-file", str(database),
        "--request", str(request),
        "--artifact-source", str(artifacts),
        "--provider", str(provider),
        "--executor-id-file", str(executor),
        "--promotion-verifier-id-file", str(verifier),
    ])

    assert status == 0
    assert capsys.readouterr().out == '{"outcome":"published"}\n'
    assert calls == ["GET", "PUT", "GET"]
    assert len(clients) == 1 and clients[0].is_closed
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT execution.status,attempt.status,"
            " (SELECT count(*) FROM release_publication_receipts)"
            " FROM release_publication_executions execution"
            " JOIN release_publication_execution_attempts attempt"
            " ON attempt.execution_id=execution.execution_id"
        )).one() == ("published", "reconciled", 1)


def test_manual_operator_boundary_publishes_exactly_once(
    ready, tmp_path: Path, monkeypatch, capsys
):
    audit_operator_publishes_once(
        engine=ready[0],
        database_url=ready[0].url.render_as_string(hide_password=False),
        candidate=ready[1],
        evidence_path=ready[2],
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
    )
