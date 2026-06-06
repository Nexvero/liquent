"""Tests für das optionale Streamlit-Setup der Visual Preview (LQ-020 Phase 2).

Kein Streamlit-Install, kein Browser, kein Netzwerk, keine Report-I/O. Prüft das
optionale ``visual``-Extra in ``pyproject.toml``, den README-Run-Hinweis und den
streamlit-freien Fallback von ``app.main()``.
"""

import importlib
import importlib.util
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _ROOT / "pyproject.toml"
_README = _ROOT / "README.md"

_STREAMLIT_AVAILABLE = importlib.util.find_spec("streamlit") is not None


def _pyproject() -> dict:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


# 1: app ist ohne Streamlit importierbar.
def test_app_importable_without_streamlit():
    module = importlib.import_module("tools.visual_preview.app")
    assert hasattr(module, "main")


# 2: main() verhält sich stabil; ohne Streamlit erscheint die klare Meldung.
def test_main_without_streamlit_is_stable(capsys):
    from tools.visual_preview import app

    if _STREAMLIT_AVAILABLE:
        # Robust: keinen echten App-Start erzwingen — nur Importbarkeit prüfen.
        assert hasattr(app, "main")
        return
    app.main()
    out = capsys.readouterr().out
    assert "Streamlit is not installed" in out
    assert "optional visual extra" in out


# 3: pyproject enthält das optionale Extra "visual" mit Streamlit.
def test_pyproject_has_visual_extra():
    data = _pyproject()
    extras = data["project"]["optional-dependencies"]
    assert "visual" in extras
    assert any(str(item).startswith("streamlit") for item in extras["visual"])
    # Bestehendes dev-Extra bleibt erhalten.
    assert "dev" in extras


# 4: Streamlit ist KEINE Pflicht-Dependency.
def test_streamlit_is_not_a_runtime_dependency():
    data = _pyproject()
    runtime = data["project"].get("dependencies", [])
    assert runtime == [] or all("streamlit" not in str(d) for d in runtime)


# 5: README enthält Installations-/Start-/Fallback-Befehle und Sicherheitsgrenzen.
def test_readme_contains_run_instructions():
    text = _README.read_text(encoding="utf-8")
    for token in (
        'pip install -e ".[visual]"',
        "streamlit run tools/visual_preview/app.py",
        "python -m tools.visual_preview.app",
    ):
        assert token in text, f"README muss {token!r} enthalten"
    lower = text.lower()
    for phrase in (
        "synthetic/local preview only",
        "no live trading",
        "no trading recommendation",
    ):
        assert phrase in lower, f"README muss Sicherheitsgrenze {phrase!r} enthalten"


# 6: Statischer Scan -> tools/visual_preview ohne harte Netzwerk-/Order-Pfade.
def test_tools_have_no_forbidden_code_paths():
    import inspect

    from tools.visual_preview import app as app_module
    from tools.visual_preview import preview_logic as logic_module

    source = (inspect.getsource(app_module) + inspect.getsource(logic_module)).lower()
    forbidden = [
        "req" + "uests",
        "url" + "lib",
        "soc" + "ket",
        "ht" + "tp://",
        "ht" + "tps://",
        "api_" + "key",
        "exch" + "ange",
        "live_" + "order",
        "place_" + "order",
        "paper_" + "trading",
        "down" + "load(",
    ]
    for token in forbidden:
        assert token not in source, f"Visual-Preview darf {token!r} nicht enthalten"
