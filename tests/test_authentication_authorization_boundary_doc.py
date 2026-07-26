from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "lq-085-authentication-authorization-boundary.md"


def test_auth_boundary_separates_identity_membership_and_permissions() -> None:
    document = DOC.read_text(encoding="utf-8")

    for concept in ("User", "Session", "Workspace Membership", "Permission"):
        assert f"| {concept} |" in document
    assert "research:read" in document
    assert "research:write" in document
    assert "aktive Workspace-Mitgliedschaft" in document


def test_auth_boundary_defines_browser_session_and_csrf_floor() -> None:
    document = DOC.read_text(encoding="utf-8")

    for requirement in (
        "`Secure`, `HttpOnly`-Cookie",
        "`SameSite=Lax`",
        "serverseitiger Widerruf",
        "CSRF-Nachweis",
        "nicht in Local Storage",
    ):
        assert requirement in document


def test_auth_boundary_is_fail_closed_without_resource_enumeration() -> None:
    document = DOC.read_text(encoding="utf-8")

    for code in (
        "authentication_required",
        "permission_denied",
        "csrf_validation_failed",
    ):
        assert code in document
    assert "Für fremde Ressourcen wird 404 verwendet" in document
    assert "scheitert die Aktion fail-closed" in document


def test_shared_environment_gate_remains_until_end_to_end_proof() -> None:
    document = DOC.read_text(encoding="utf-8")

    assert "LQ-084 bleibt unverändert aktiv" in document
    assert "keine Freischaltung für Preview/Produktion" in document
    assert "kein Release oder Deployment" in document
    assert "keine Auswahl zwischen OAuth, Passkeys, Magic Link" in document
