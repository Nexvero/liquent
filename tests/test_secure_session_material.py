import pytest

from liquent_platform.identity import secure_material
from liquent_platform.identity.ports import BrowserSessionMaterialGenerator
from liquent_platform.identity.secure_material import (
    MINIMUM_ENTROPY_BYTES,
    SecureBrowserSessionMaterialGenerator,
)
from liquent_platform.identity.session import SessionId


def _generate(port: BrowserSessionMaterialGenerator) -> tuple[SessionId, str]:
    return port.new_session_id(), port.new_csrf_token()


def test_generator_uses_independent_urlsafe_draws_with_minimum_entropy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    values = iter(["opaque-session", "private-csrf-proof"])

    def token_urlsafe(entropy_bytes: int) -> str:
        calls.append(entropy_bytes)
        return next(values)

    monkeypatch.setattr(secure_material.secrets, "token_urlsafe", token_urlsafe)
    generator = SecureBrowserSessionMaterialGenerator()

    session_id, csrf_token = _generate(generator)

    assert session_id == SessionId("opaque-session")
    assert csrf_token == "private-csrf-proof"
    assert calls == [MINIMUM_ENTROPY_BYTES, MINIMUM_ENTROPY_BYTES]


def test_generator_allows_stronger_entropy_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        secure_material.secrets,
        "token_urlsafe",
        lambda entropy_bytes: calls.append(entropy_bytes) or "value",
    )
    generator = SecureBrowserSessionMaterialGenerator(48)

    _generate(generator)

    assert calls == [48, 48]


@pytest.mark.parametrize("entropy_bytes", [0, 31, True, 32.0])
def test_generator_rejects_invalid_or_weak_entropy(
    entropy_bytes: object,
) -> None:
    with pytest.raises(ValueError, match="session entropy must be at least 32 bytes"):
        SecureBrowserSessionMaterialGenerator(entropy_bytes)  # type: ignore[arg-type]
