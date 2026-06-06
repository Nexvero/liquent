"""Tests für die CLI-Kostenmodell-Parameter --fee-rate/--spread/--slippage (LQ-012).

In-process über ``main(argv)`` + ``tmp_path``. Reale CostModel-Felder
(``fee_rate``, ``spread``, ``slippage``); KEINE ``*_bps``. Default 0.0/0.0/0.0
bleibt frictionless/rückwärtskompatibel. Keine echten Daten, keine Reports
committed, keine Netzwerk-/Live-/Paper-Trading-Pfade.
"""

from pathlib import Path

from liquent.cli.backtest_mid_breakout import main

_FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return str(_FIXTURES / name)


def _args(output: Path, *extra: str) -> list[str]:
    return [
        "--csv", _fixture("strategy_mid_breakout_long.csv"),
        "--output", str(output),
        "--symbol", "TESTUSDT",
        "--exchange", "synthetic",
        "--asset-class", "crypto",
        *extra,
    ]


# 1: CLI ohne Kostenparameter -> frictionless, Cost-Model-Abschnitt mit 0.0.
def test_cli_default_is_frictionless(tmp_path, capsys):
    out = tmp_path / "report.md"
    assert main(_args(out)) == 0
    text = out.read_text(encoding="utf-8")
    assert "## Cost Model" in text
    assert "| fee_rate | 0.0 |" in text
    assert "| spread | 0.0 |" in text
    assert "| slippage | 0.0 |" in text
    # Runner-Parameter bleiben frictionless.
    assert "| frictionless | True |" in text
    # Terminal-Hinweis vorhanden.
    assert "cost_model: fee_rate=0.0 spread=0.0 slippage=0.0" in capsys.readouterr().out


# 2: --fee-rate wird akzeptiert und erscheint im Report.
def test_cli_accepts_fee_rate(tmp_path):
    out = tmp_path / "report.md"
    assert main(_args(out, "--fee-rate", "0.001")) == 0
    text = out.read_text(encoding="utf-8")
    assert "| fee_rate | 0.001 |" in text
    assert "| frictionless | False |" in text


# 3: --spread wird akzeptiert und erscheint im Report.
def test_cli_accepts_spread(tmp_path):
    out = tmp_path / "report.md"
    assert main(_args(out, "--spread", "0.05")) == 0
    assert "| spread | 0.05 |" in out.read_text(encoding="utf-8")


# 4: --slippage wird akzeptiert und erscheint im Report.
def test_cli_accepts_slippage(tmp_path):
    out = tmp_path / "report.md"
    assert main(_args(out, "--slippage", "0.0005")) == 0
    assert "| slippage | 0.0005 |" in out.read_text(encoding="utf-8")


# 5: Alle drei zusammen werden übernommen.
def test_cli_accepts_all_three(tmp_path, capsys):
    out = tmp_path / "report.md"
    rc = main(_args(
        out, "--fee-rate", "0.002", "--spread", "0.1", "--slippage", "0.0007"
    ))
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "| fee_rate | 0.002 |" in text
    assert "| spread | 0.1 |" in text
    assert "| slippage | 0.0007 |" in text
    assert "cost_model: fee_rate=0.002 spread=0.1 slippage=0.0007" in capsys.readouterr().out


# 6: negative --fee-rate -> abgelehnt, keine Datei.
def test_cli_negative_fee_rate_rejected(tmp_path):
    out = tmp_path / "report.md"
    assert main(_args(out, "--fee-rate", "-0.001")) != 0
    assert not out.exists()


# 7: negative --spread -> abgelehnt, keine Datei.
def test_cli_negative_spread_rejected(tmp_path):
    out = tmp_path / "report.md"
    assert main(_args(out, "--spread", "-0.05")) != 0
    assert not out.exists()


# 8: negative --slippage -> abgelehnt, keine Datei.
def test_cli_negative_slippage_rejected(tmp_path):
    out = tmp_path / "report.md"
    assert main(_args(out, "--slippage", "-0.0005")) != 0
    assert not out.exists()


# 9: Strategy- und Cost-Model-Abschnitt erscheinen gemeinsam (v1 + Kosten).
def test_cli_strategy_and_cost_sections_together(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v1", "--fee-rate", "0.001"))
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "## Strategy" in text
    assert "## Cost Model" in text
    assert text.index("## Strategy") < text.index("## Cost Model") < text.index("## Metrics")


# 10: Determinismus -> zwei identische Läufe liefern byte-identische Reports.
def test_cli_cost_report_deterministic(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    assert main(_args(a, "--fee-rate", "0.001", "--spread", "0.02")) == 0
    assert main(_args(b, "--fee-rate", "0.001", "--spread", "0.02")) == 0
    assert a.read_bytes() == b.read_bytes()
