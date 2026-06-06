"""Statische App-/Safety-Tests für den CSV-Modus der Visual Preview (LQ-022).

Kein Streamlit-E2E, kein Browser, kein Netzwerk. Prüft, dass die App ohne
Streamlit importierbar bleibt, den CSV-Pfad nutzt und keine Datei-Schreib-/
Netzwerk-Codepfade enthält.
"""

import importlib
import inspect


def _app_source() -> str:
    return inspect.getsource(importlib.import_module("tools.visual_preview.app"))


# 1: app.py ist ohne Streamlit importierbar.
def test_app_importable_without_streamlit():
    module = importlib.import_module("tools.visual_preview.app")
    assert hasattr(module, "main")


# 2: app.py bindet den CSV-Upload ein.
def test_app_uses_file_uploader():
    assert "file_uploader" in _app_source()


# 3: app.py nutzt den CSV-Parser.
def test_app_uses_csv_parser():
    assert "build_dataset_from_csv_text" in _app_source()


# 3a: app.py zeigt das Sample-Template via st.code.
def test_app_shows_sample_template():
    src = _app_source()
    assert "SAMPLE_CSV_TEMPLATE" in src
    assert ".code(" in src


# 3b: kein Download-Button in Phase 2.
def test_app_has_no_download_button():
    assert "download_button" not in _app_source()


# 4: app.py enthält keine Datei-Schreibpfade.
def test_app_has_no_file_write_paths():
    src = _app_source()
    for token in ("open(", "write(", "write_text", "write_bytes", "to_csv"):
        assert token not in src, f"app.py darf {token!r} nicht enthalten"


# 5: Statischer Scan tools/visual_preview -> keine harten Netzwerk-/Order-Pfade.
def test_tools_have_no_forbidden_code_paths():
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
