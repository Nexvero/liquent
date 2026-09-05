import pytest

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import (
    ManifestHandoffSupervisorEngineApiOperation as Operation,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_response_policy import (
    AuthorizedManifestHandoffSupervisorEngineApiResponse,
    ClosedManifestHandoffSupervisorEngineApiResponsePolicy,
)


POLICY = ClosedManifestHandoffSupervisorEngineApiResponsePolicy()


@pytest.mark.parametrize("operation,status,body,root", (
    (Operation.FIND, 200, b"[]", b"[]"),
    (Operation.CREATE, 201, b'{"Id":"a"}', b'{"Id":"a"}'),
    (Operation.INSPECT, 200, b'{"Id":"a"}', b'{"Id":"a"}'),
    (Operation.WAIT, 200, b'{"StatusCode":0}', b'{"StatusCode":0}'),
))
def test_json_successes_preserve_the_bounded_daemon_body(
    operation, status, body, root,
) -> None:
    assert POLICY.authorize(operation, status, "application/json", body) == (
        AuthorizedManifestHandoffSupervisorEngineApiResponse(
            status, "application/json", root
        )
    )


@pytest.mark.parametrize("operation,status", (
    (Operation.START, 204),
    (Operation.STOP, 204),
    (Operation.STOP, 304),
    (Operation.KILL, 204),
    (Operation.KILL, 304),
))
def test_empty_successes_have_no_media_type_or_body(operation, status) -> None:
    assert POLICY.authorize(operation, status, None, b"").body == b""


@pytest.mark.parametrize("content_type,body", (
    (None, b""),
    ("application/json", b"{}"),
))
def test_inspect_absence_is_normalized_without_daemon_detail(content_type, body) -> None:
    result = POLICY.authorize(Operation.INSPECT, 404, content_type, body)
    assert result == AuthorizedManifestHandoffSupervisorEngineApiResponse(404, None, b"")


@pytest.mark.parametrize("operation,status", (
    (Operation.FIND, 500),
    (Operation.CREATE, 409),
    (Operation.INSPECT, 500),
    (Operation.START, 404),
    (Operation.WAIT, 500),
    (Operation.STOP, 500),
    (Operation.KILL, 500),
))
def test_daemon_error_status_and_body_are_rejected_detail_free(operation, status) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        POLICY.authorize(operation, status, "application/json", b'{"message":"secret"}')
    assert str(caught.value) == "manifest_handoff_registry_unavailable"
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("content_type", (
    None, "application/json; charset=utf-8", "text/plain", "Application/Json",
))
def test_json_success_requires_the_exact_media_type(content_type) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        POLICY.authorize(Operation.FIND, 200, content_type, b"[]")


@pytest.mark.parametrize("operation,status,content_type,body", (
    (Operation.FIND, 200, "application/json", b"{}"),
    (Operation.CREATE, 201, "application/json", b"[]"),
    (Operation.WAIT, 200, "application/json", b'{"a":1,"a":2}'),
    (Operation.START, 204, None, b"{}"),
    (Operation.STOP, 304, "application/json", b""),
    (Operation.INSPECT, 404, "application/json", b'{"message":"missing"}'),
))
def test_wrong_shape_duplicates_or_empty_response_extensions_fail_closed(
    operation, status, content_type, body,
) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        POLICY.authorize(operation, status, content_type, body)


def test_json_body_limit_is_closed() -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        POLICY.authorize(
            Operation.FIND, 200, "application/json", b"[" + b" " * 1_048_575 + b"]"
        )


def test_invalid_caller_types_and_non_operation_values_fail_closed() -> None:
    for values in (
        ("find", 200, "application/json", b"[]"),
        (Operation.FIND, True, "application/json", b"[]"),
        (Operation.FIND, 200, 1, b"[]"),
        (Operation.FIND, 200, "application/json", bytearray(b"[]")),
    ):
        with pytest.raises(ManifestHandoffRegistryUnavailable):
            POLICY.authorize(*values)


def test_policy_has_no_listener_connect_forward_or_close_surface() -> None:
    surface = vars(ClosedManifestHandoffSupervisorEngineApiResponsePolicy)
    for name in ("listen", "bind", "connect", "request", "forward", "close"):
        assert name not in surface
