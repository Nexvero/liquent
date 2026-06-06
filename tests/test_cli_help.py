"""Tests für die CLI-Hilfe von ``backtest_mid_breakout`` (LQ-018 Phase 2).

Robuste Substring-Checks (kein fragiler Snapshot). ``--help`` wird in einem
Subprozess mit ``sys.executable`` aufgerufen — kein Datenlauf, keine Report-
Datei, kein Netzwerk. Sichert insbesondere den behobenen ``%``-Help-Bug ab
(`--help` muss mit Exit 0 laufen).
"""

import subprocess
import sys
from pathlib import Path

_README = Path(__file__).resolve().parents[1] / "README.md"


def _help_output() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "liquent.cli.backtest_mid_breakout", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"--help muss mit Exit 0 laufen (war {result.returncode})\n{result.stderr}"
    )
    return result.stdout


# 1: --help läuft erfolgreich (Exit 0) — deckt den behobenen %-Bug ab.
def test_help_runs_successfully():
    out = _help_output()
    assert "usage:" in out
    assert "show this help message and exit" in out


# 2: Help enthält die zentralen Flags.
def test_help_contains_core_flags():
    out = _help_output()
    for flag in (
        "--strategy", "--lookback-bars", "--stop-distance-pct", "--min-strength",
        "--breakout-threshold-pct", "--cooldown-bars", "--max-signals-per-day",
        "--fee-rate", "--spread", "--slippage",
    ):
        assert flag in out, f"Help muss {flag} enthalten"


# 3: Help weist auf den v0-Default hin (umbruchsicher).
def test_help_mentions_v0_default():
    out = _help_output()
    assert "Default: v0" in out


# 4: Help weist auf v1-only Parameter hin.
def test_help_mentions_v1_only():
    out = _help_output()
    assert "Only valid with --strategy v1" in out


# 5: Help enthält die Cost-Model-Hinweise.
def test_help_mentions_cost_model():
    out = _help_output()
    assert "notional fraction" in out
    assert "Absolute spread cost per unit" in out


# 6: Help enthält keine Bewertungs-/Profitabilitätsbegriffe.
def test_help_has_no_evaluation_terms():
    out = _help_output().lower()
    for token in ("profitable", "better", "worse", "winner", "recommended"):
        assert token not in out, f"Help darf {token!r} nicht enthalten"


# 7: argparse-Gruppen erscheinen in der Hilfe.
def test_help_contains_argument_groups():
    out = _help_output()
    for group in (
        "Data input:", "Strategy selection:", "Strategy parameters:",
        "Strategy v1 parameters:", "Risk / Backtest:", "Cost model:",
        "Output / Reporting:",
    ):
        assert group in out, f"Help muss Gruppe {group!r} enthalten"


# 8: README enthält konsistente CLI-Beispiele und Flags.
def test_readme_contains_cli_examples():
    text = _README.read_text(encoding="utf-8")
    for token in (
        "python -m liquent.cli.backtest_mid_breakout",
        "--strategy v0", "--strategy v1",
        "--breakout-threshold-pct", "--cooldown-bars", "--max-signals-per-day",
        "--fee-rate", "--spread", "--slippage",
    ):
        assert token in text, f"README muss {token!r} enthalten"
