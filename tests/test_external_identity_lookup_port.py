from liquent_platform.identity.access import UserId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.ports import ExternalIdentityLookup


KNOWN = ExternalIdentity("https://issuer.example", "subject-123")
UNKNOWN = ExternalIdentity("https://issuer.example", "other-subject")


class StubExternalIdentityLookup:
    def __init__(self, mapping: dict[ExternalIdentity, UserId] | None = None) -> None:
        self._mapping = mapping or {}
        self.calls: list[ExternalIdentity] = []

    def get_user_id(self, identity: ExternalIdentity) -> UserId | None:
        self.calls.append(identity)
        return self._mapping.get(identity)


def _lookup(
    port: ExternalIdentityLookup, identity: ExternalIdentity
) -> UserId | None:
    return port.get_user_id(identity)


def test_returns_existing_user_id() -> None:
    store = StubExternalIdentityLookup({KNOWN: UserId("user-1")})

    assert _lookup(store, KNOWN) == UserId("user-1")
    assert store.calls == [KNOWN]


def test_unknown_identity_is_neutral_none() -> None:
    store = StubExternalIdentityLookup({KNOWN: UserId("user-1")})

    assert _lookup(store, UNKNOWN) is None


def test_case_or_slash_variant_does_not_resolve() -> None:
    store = StubExternalIdentityLookup({KNOWN: UserId("user-1")})

    assert _lookup(store, ExternalIdentity("https://Issuer.Example", "subject-123")) is None
    assert _lookup(store, ExternalIdentity("https://issuer.example/", "subject-123")) is None
    assert _lookup(store, ExternalIdentity("https://issuer.example", "Subject-123")) is None
