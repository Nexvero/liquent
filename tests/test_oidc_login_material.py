import base64
import hashlib
import inspect
from dataclasses import FrozenInstanceError, fields

import pytest

import liquent_platform.identity.oidc_login_material as mod
from liquent_platform.identity.oidc_login_material import (
    OidcLoginMaterial,
    SecureOidcLoginMaterialGenerator,
)


# RFC 7636 Appendix B test vector.
RFC_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
RFC_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def _material() -> OidcLoginMaterial:
    return OidcLoginMaterial("state-x", "nonce-y", "verifier-z", "challenge-c")


# --- Model -----------------------------------------------------------------

def test_model_is_immutable() -> None:
    material = _material()

    with pytest.raises(FrozenInstanceError):
        material.state = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("state", "nonce", "code_verifier", "code_challenge", "message"),
    [
        ("", "n", "v", "c", "state must not be empty"),
        ("s", "", "v", "c", "nonce must not be empty"),
        ("s", "n", "", "c", "code_verifier must not be empty"),
        ("s", "n", "v", "", "code_challenge must not be empty"),
    ],
)
def test_all_four_fields_must_be_non_empty(
    state: str, nonce: str, code_verifier: str, code_challenge: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        OidcLoginMaterial(state, nonce, code_verifier, code_challenge)


def test_repr_hides_secrets_and_shows_challenge() -> None:
    material = OidcLoginMaterial(
        "secret-state", "secret-nonce", "secret-verifier", "public-challenge"
    )
    text = repr(material)

    assert "secret-state" not in text
    assert "secret-nonce" not in text
    assert "secret-verifier" not in text
    assert "public-challenge" in text


def test_model_has_exactly_the_four_agreed_fields() -> None:
    names = [f.name for f in fields(OidcLoginMaterial)]

    assert names == ["state", "nonce", "code_verifier", "code_challenge"]


# --- Generator draws -------------------------------------------------------

def _record_draws(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []

    def fake(nbytes: int) -> str:
        calls.append(nbytes)
        return f"draw-{len(calls)}"

    monkeypatch.setattr(mod.secrets, "token_urlsafe", fake)
    return calls


def test_generator_makes_three_independent_urlsafe_draws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _record_draws(monkeypatch)

    material = SecureOidcLoginMaterialGenerator().new_login_material()

    assert len(calls) == 3
    drawn = {material.state, material.nonce, material.code_verifier}
    assert drawn == {"draw-1", "draw-2", "draw-3"}  # three distinct, independent


def test_each_draw_uses_default_32_entropy_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _record_draws(monkeypatch)

    SecureOidcLoginMaterialGenerator().new_login_material()

    assert calls == [32, 32, 32]


def test_stronger_entropy_is_used_for_all_three_draws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _record_draws(monkeypatch)

    SecureOidcLoginMaterialGenerator(48).new_login_material()

    assert calls == [48, 48, 48]


def test_minimum_32_bytes_is_accepted() -> None:
    material = SecureOidcLoginMaterialGenerator(32).new_login_material()

    assert material.code_verifier  # constructed successfully


def test_maximum_96_bytes_used_for_all_three_draws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _record_draws(monkeypatch)

    SecureOidcLoginMaterialGenerator(96).new_login_material()

    assert calls == [96, 96, 96]


def test_maximum_96_bytes_produces_128_char_verifier() -> None:
    # RFC 7636 allows 43..128 chars; token_urlsafe(96) yields exactly 128.
    material = SecureOidcLoginMaterialGenerator(96).new_login_material()

    assert len(material.code_verifier) == 128


@pytest.mark.parametrize("entropy_bytes", [True, False, 31, 16, 97, 128, "32", 32.0])
def test_weak_or_invalid_entropy_is_rejected(entropy_bytes: object) -> None:
    with pytest.raises(
        ValueError, match="login material entropy must be between 32 and 96 bytes"
    ):
        SecureOidcLoginMaterialGenerator(entropy_bytes)  # type: ignore[arg-type]


# --- PKCE S256 challenge ---------------------------------------------------

def test_challenge_matches_known_s256_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(["state-x", "nonce-y", RFC_VERIFIER])
    monkeypatch.setattr(mod.secrets, "token_urlsafe", lambda nbytes: next(values))

    material = SecureOidcLoginMaterialGenerator().new_login_material()

    assert material.code_verifier == RFC_VERIFIER
    assert material.code_challenge == RFC_CHALLENGE


def test_challenge_is_base64url_without_padding() -> None:
    material = SecureOidcLoginMaterialGenerator().new_login_material()

    assert "=" not in material.code_challenge
    assert set(material.code_challenge) <= set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    )
    assert len(material.code_challenge) == 43  # SHA-256 -> 43 base64url chars


def test_challenge_depends_only_on_code_verifier() -> None:
    material = SecureOidcLoginMaterialGenerator().new_login_material()

    expected = (
        base64.urlsafe_b64encode(
            hashlib.sha256(material.code_verifier.encode("ascii")).digest()
        )
        .rstrip(b"=")
        .decode("ascii")
    )

    assert material.code_challenge == expected


# --- Structural boundaries -------------------------------------------------

def test_generator_takes_only_entropy_bytes_and_has_no_plain_option() -> None:
    parameters = list(
        inspect.signature(SecureOidcLoginMaterialGenerator.__init__).parameters
    )

    assert parameters == ["self", "entropy_bytes"]
    assert "plain" not in inspect.getsource(mod).lower()


def test_module_defines_no_ports_stores_or_routes() -> None:
    source = inspect.getsource(mod)

    assert "Protocol" not in source
    assert "Store" not in source
    assert "fastapi" not in source
    assert "router" not in source.lower()
