import inspect
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest

import liquent_platform.application.prepare_oidc_login_authorization as module
from liquent_platform.application.build_oidc_authorization_request import (
    OidcAuthorizationRequest,
)
from liquent_platform.application.oidc_login_errors import (
    OidcLoginStartConflict,
    OidcLoginUnavailable,
)
from liquent_platform.application.prepare_oidc_login_authorization import (
    prepare_oidc_login_authorization,
)
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_login_material import OidcLoginMaterial
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)


NOW = datetime(2026, 8, 4, 12, tzinfo=UTC)
LIFETIME = timedelta(minutes=10)
ADMISSION = IdentityAdmissionId("admission-1")
RETURN_PATH = "/workspaces/w-1/research"

ISSUER = "https://idp.example.test"
ENDPOINT = "https://idp.example.test/authorize"
CLIENT_ID = "liquent-control-plane"
REDIRECT_URI = "https://app.example.test/v1/oidc/callback"
SCOPES = ("openid", "email")


def _configuration(client_id: str = CLIENT_ID) -> TrustedOidcClientConfiguration:
    return TrustedOidcClientConfiguration(
        issuer=ISSUER,
        authorization_endpoint=ENDPOINT,
        client_id=client_id,
        redirect_uri=REDIRECT_URI,
        scopes=SCOPES,
    )


class Recorder:
    """Shared call log so order and non-invocation can be asserted exactly."""

    def __init__(self) -> None:
        self.calls: list[str] = []


class StubLookup:
    def __init__(
        self,
        recorder: Recorder,
        configuration: TrustedOidcClientConfiguration | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._recorder = recorder
        self.configuration = configuration
        self._error = error
        self.calls = 0

    def get_active_configuration(self) -> TrustedOidcClientConfiguration | None:
        self.calls += 1
        self._recorder.calls.append("lookup")
        if self._error is not None:
            raise self._error
        return self.configuration


class RotatingLookup:
    """Returns a different configuration on every call, to expose a re-read."""

    def __init__(self, recorder: Recorder) -> None:
        self._recorder = recorder
        self.calls = 0
        self.handed_out: list[TrustedOidcClientConfiguration] = []

    def get_active_configuration(self) -> TrustedOidcClientConfiguration | None:
        self.calls += 1
        self._recorder.calls.append("lookup")
        configuration = _configuration(f"client-{self.calls}")
        self.handed_out.append(configuration)
        return configuration


class StubGenerator:
    def __init__(
        self, recorder: Recorder, *, error: Exception | None = None
    ) -> None:
        self._recorder = recorder
        self._error = error
        self.calls = 0

    def new_login_material(self) -> OidcLoginMaterial:
        self.calls += 1
        self._recorder.calls.append("generator")
        if self._error is not None:
            raise self._error
        return OidcLoginMaterial(
            "generated-state",
            "generated-nonce",
            "generated-verifier",
            "generated-challenge",
        )


class StubStore:
    def __init__(
        self,
        recorder: Recorder,
        *,
        added: bool = True,
        error: Exception | None = None,
    ) -> None:
        self._recorder = recorder
        self._added = added
        self._error = error
        self.calls: list[tuple[OidcLoginState, PendingOidcLoginTransaction]] = []

    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool:
        self.calls.append((state, transaction))
        self._recorder.calls.append("store")
        if self._error is not None:
            raise self._error
        return self._added


def _prepare(
    lookup: Any, store: Any, generator: Any, **overrides: Any
) -> OidcAuthorizationRequest:
    arguments: dict[str, Any] = {"now": NOW, "lifetime": LIFETIME}
    arguments.update(overrides)
    return prepare_oidc_login_authorization(
        lookup, store, generator, **arguments
    )


def _parameters(request: OidcAuthorizationRequest) -> dict[str, str]:
    return dict(parse_qsl(urlsplit(request.url).query, keep_blank_values=True))


# --- Success flow -----------------------------------------------------------

def test_success_returns_an_authorization_request() -> None:
    recorder = Recorder()
    request = _prepare(
        StubLookup(recorder, _configuration()),
        StubStore(recorder),
        StubGenerator(recorder),
    )

    assert isinstance(request, OidcAuthorizationRequest)


def test_every_dependency_is_used_exactly_once_and_in_order() -> None:
    recorder = Recorder()
    lookup = StubLookup(recorder, _configuration())
    store = StubStore(recorder)
    generator = StubGenerator(recorder)

    _prepare(lookup, store, generator)

    assert lookup.calls == 1
    assert generator.calls == 1
    assert len(store.calls) == 1
    assert recorder.calls == ["lookup", "generator", "store"]


def test_the_request_is_built_only_after_the_store_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder()
    original = module.build_oidc_authorization_request

    def spy(configuration: Any, started: Any) -> OidcAuthorizationRequest:
        recorder.calls.append("builder")
        return original(configuration, started)

    monkeypatch.setattr(module, "build_oidc_authorization_request", spy)

    _prepare(
        StubLookup(recorder, _configuration()),
        StubStore(recorder),
        StubGenerator(recorder),
    )

    assert recorder.calls == ["lookup", "generator", "store", "builder"]
    assert recorder.calls.count("builder") == 1


def test_the_builder_receives_exactly_the_looked_up_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder()
    configuration = _configuration()
    seen: list[Any] = []
    original = module.build_oidc_authorization_request

    def spy(passed: Any, started: Any) -> OidcAuthorizationRequest:
        seen.append(passed)
        return original(passed, started)

    monkeypatch.setattr(module, "build_oidc_authorization_request", spy)

    _prepare(
        StubLookup(recorder, configuration),
        StubStore(recorder),
        StubGenerator(recorder),
    )

    assert seen == [configuration]
    assert seen[0] is configuration


# --- Data flow into the pending record and the request ----------------------

def test_the_pending_record_carries_the_configured_issuer_and_redirect_uri() -> None:
    recorder = Recorder()
    store = StubStore(recorder)

    _prepare(StubLookup(recorder, _configuration()), store, StubGenerator(recorder))

    _state, pending = store.calls[0]
    assert pending.expected_issuer == ISSUER
    assert pending.redirect_uri == REDIRECT_URI


def test_the_request_carries_the_same_configuration_values() -> None:
    recorder = Recorder()
    request = _prepare(
        StubLookup(recorder, _configuration()),
        StubStore(recorder),
        StubGenerator(recorder),
    )

    assert request.url.split("?", 1)[0] == ENDPOINT
    parameters = _parameters(request)
    assert parameters["client_id"] == CLIENT_ID
    assert parameters["redirect_uri"] == REDIRECT_URI
    assert parameters["scope"] == "openid email"


def test_now_and_lifetime_are_passed_through_exactly() -> None:
    recorder = Recorder()
    store = StubStore(recorder)

    _prepare(
        StubLookup(recorder, _configuration()),
        store,
        StubGenerator(recorder),
        lifetime=timedelta(minutes=3),
    )

    _state, pending = store.calls[0]
    assert pending.created_at == NOW
    assert pending.expires_at == NOW + timedelta(minutes=3)


def test_admission_and_return_path_are_bound_server_side() -> None:
    recorder = Recorder()
    store = StubStore(recorder)

    _prepare(
        StubLookup(recorder, _configuration()),
        store,
        StubGenerator(recorder),
        admission_id=ADMISSION,
        return_path=RETURN_PATH,
    )

    _state, pending = store.calls[0]
    assert pending.admission_id is ADMISSION
    assert pending.return_path == RETURN_PATH


def test_admission_and_return_path_never_reach_the_request() -> None:
    recorder = Recorder()
    request = _prepare(
        StubLookup(recorder, _configuration()),
        StubStore(recorder),
        StubGenerator(recorder),
        admission_id=ADMISSION,
        return_path=RETURN_PATH,
    )

    parameters = _parameters(request)
    assert "admission_id" not in parameters
    assert "return_path" not in parameters
    assert ADMISSION.value not in request.url
    assert RETURN_PATH not in request.url


def test_the_code_verifier_stays_in_the_pending_record_only() -> None:
    recorder = Recorder()
    store = StubStore(recorder)

    request = _prepare(
        StubLookup(recorder, _configuration()), store, StubGenerator(recorder)
    )

    _state, pending = store.calls[0]
    assert pending.code_verifier == "generated-verifier"
    assert "generated-verifier" not in request.url
    assert "code_verifier" not in _parameters(request)


def test_the_returned_repr_hides_the_url_state_and_nonce() -> None:
    recorder = Recorder()
    request = _prepare(
        StubLookup(recorder, _configuration()),
        StubStore(recorder),
        StubGenerator(recorder),
    )
    text = repr(request)

    assert "OidcAuthorizationRequest" in text
    for secret in (request.url, "generated-state", "generated-nonce", ENDPOINT):
        assert secret not in text


# --- Structural protection --------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "issuer",
        "expected_issuer",
        "authorization_endpoint",
        "endpoint",
        "client_id",
        "redirect_uri",
        "scope",
        "scopes",
        "provider",
        "tenant",
        "workspace_id",
        "user_id",
        "host",
        "headers",
        "request",
        "response",
    ],
)
def test_the_signature_has_no_configuration_or_transport_parameter(
    name: str,
) -> None:
    parameters = inspect.signature(prepare_oidc_login_authorization).parameters

    assert name not in parameters


def test_the_signature_is_exactly_the_agreed_one() -> None:
    parameters = inspect.signature(prepare_oidc_login_authorization).parameters

    assert list(parameters) == [
        "configuration_lookup",
        "transaction_store",
        "generator",
        "now",
        "lifetime",
        "admission_id",
        "return_path",
    ]
    # The clock is injected; there is no default that could hide a real clock.
    assert parameters["now"].default is inspect.Parameter.empty
    assert parameters["lifetime"].default is inspect.Parameter.empty
    assert parameters["admission_id"].default is None
    assert parameters["return_path"].default is None


def test_the_return_annotation_is_the_authorization_request() -> None:
    annotation = inspect.signature(
        prepare_oidc_login_authorization
    ).return_annotation

    assert annotation is OidcAuthorizationRequest


# --- No active configuration ------------------------------------------------

def test_a_missing_configuration_raises_the_neutral_error() -> None:
    recorder = Recorder()

    with pytest.raises(OidcLoginUnavailable) as raised:
        _prepare(StubLookup(recorder, None), StubStore(recorder), StubGenerator(recorder))

    assert raised.value.code == "oidc_login_unavailable"


def test_the_unavailable_error_carries_no_configuration_detail() -> None:
    recorder = Recorder()

    with pytest.raises(OidcLoginUnavailable) as raised:
        _prepare(StubLookup(recorder, None), StubStore(recorder), StubGenerator(recorder))

    text = f"{raised.value!r} {raised.value!s} {raised.value.args}"
    for secret in (ISSUER, ENDPOINT, CLIENT_ID, REDIRECT_URI, "openid"):
        assert secret not in text


def test_a_missing_configuration_touches_nothing_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder()
    monkeypatch.setattr(
        module,
        "build_oidc_authorization_request",
        lambda *_a, **_k: pytest.fail("builder must not run"),
    )
    store = StubStore(recorder)
    generator = StubGenerator(recorder)

    with pytest.raises(OidcLoginUnavailable):
        _prepare(StubLookup(recorder, None), store, generator)

    assert generator.calls == 0
    assert store.calls == []
    assert recorder.calls == ["lookup"]


# --- Error propagation ------------------------------------------------------

def test_a_lookup_failure_propagates_and_stops_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder()
    monkeypatch.setattr(
        module,
        "build_oidc_authorization_request",
        lambda *_a, **_k: pytest.fail("builder must not run"),
    )
    store = StubStore(recorder)
    generator = StubGenerator(recorder)

    with pytest.raises(RuntimeError, match="configuration source unavailable"):
        _prepare(
            StubLookup(recorder, error=RuntimeError("configuration source unavailable")),
            store,
            generator,
        )

    assert generator.calls == 0
    assert store.calls == []


def test_a_creation_conflict_propagates_and_stops_before_the_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder()
    monkeypatch.setattr(
        module,
        "build_oidc_authorization_request",
        lambda *_a, **_k: pytest.fail("builder must not run"),
    )
    lookup = StubLookup(recorder, _configuration())
    store = StubStore(recorder, added=False)
    generator = StubGenerator(recorder)

    with pytest.raises(OidcLoginStartConflict):
        _prepare(lookup, store, generator)

    # No retry: no second lookup, generator, or store call.
    assert lookup.calls == 1
    assert generator.calls == 1
    assert len(store.calls) == 1


def test_a_store_failure_propagates_unchanged() -> None:
    recorder = Recorder()

    with pytest.raises(RuntimeError, match="store unavailable"):
        _prepare(
            StubLookup(recorder, _configuration()),
            StubStore(recorder, error=RuntimeError("store unavailable")),
            StubGenerator(recorder),
        )


def test_a_generator_failure_propagates_unchanged() -> None:
    recorder = Recorder()
    store = StubStore(recorder)

    with pytest.raises(RuntimeError, match="entropy unavailable"):
        _prepare(
            StubLookup(recorder, _configuration()),
            store,
            StubGenerator(recorder, error=RuntimeError("entropy unavailable")),
        )

    assert store.calls == []


def test_a_builder_failure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder()

    def boom(*_args: Any, **_kwargs: Any) -> OidcAuthorizationRequest:
        raise RuntimeError("builder exploded")

    monkeypatch.setattr(module, "build_oidc_authorization_request", boom)

    with pytest.raises(RuntimeError, match="builder exploded"):
        _prepare(
            StubLookup(recorder, _configuration()),
            StubStore(recorder),
            StubGenerator(recorder),
        )


# --- Time bounds stay with start_oidc_login ---------------------------------

@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"lifetime": timedelta(0)}, "lifetime must be positive"),
        ({"now": datetime(2026, 8, 4, 12)}, "now must be timezone-aware"),
    ],
)
def test_invalid_time_bounds_are_still_rejected_by_the_start_use_case(
    overrides: dict[str, Any], message: str
) -> None:
    recorder = Recorder()
    lookup = StubLookup(recorder, _configuration())
    store = StubStore(recorder)
    generator = StubGenerator(recorder)

    with pytest.raises(ValueError, match=message):
        _prepare(lookup, store, generator, **overrides)

    # The read-only lookup may already have run; drawing material and storing
    # must not have, because LQ-144 validates before generating.
    assert lookup.calls == 1
    assert generator.calls == 0
    assert store.calls == []
    assert recorder.calls == ["lookup"]


# --- Snapshot consistency ---------------------------------------------------

def test_one_start_reads_the_configuration_only_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder()
    lookup = RotatingLookup(recorder)
    store = StubStore(recorder)
    seen: list[Any] = []
    original = module.build_oidc_authorization_request

    def spy(passed: Any, started: Any) -> OidcAuthorizationRequest:
        seen.append(passed)
        return original(passed, started)

    monkeypatch.setattr(module, "build_oidc_authorization_request", spy)

    request = _prepare(lookup, store, StubGenerator(recorder))

    assert lookup.calls == 1
    first = lookup.handed_out[0]
    # Pending record and request both come from that one snapshot.
    _state, pending = store.calls[0]
    assert pending.expected_issuer == first.issuer
    assert pending.redirect_uri == first.redirect_uri
    assert seen[0] is first
    assert _parameters(request)["client_id"] == "client-1"


def test_two_separate_calls_may_each_read_a_newer_snapshot() -> None:
    recorder = Recorder()
    lookup = RotatingLookup(recorder)

    first = _prepare(lookup, StubStore(recorder), StubGenerator(recorder))
    second = _prepare(lookup, StubStore(recorder), StubGenerator(recorder))

    assert lookup.calls == 2
    assert _parameters(first)["client_id"] == "client-1"
    assert _parameters(second)["client_id"] == "client-2"
