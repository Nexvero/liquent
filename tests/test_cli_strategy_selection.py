"""Tests für die CLI-Strategieauswahl --strategy v0|v1 (LQ-009 Phase 2).

In-process über ``main(argv)`` — kein Subprozess, kein Netzwerk. Nutzt
``tmp_path`` für die Ausgabe und die bestehenden synthetischen Fixtures. Reine
Analyse, keine echten Daten, keine Reports unter data/raw, keine Zugangsdaten.
"""

from pathlib import Path

from liquent.cli.backtest_mid_breakout import main

_FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return str(_FIXTURES / name)


def _args(output: Path, *extra: str, csv_name: str = "strategy_mid_breakout_long.csv") -> list[str]:
    return [
        "--csv", _fixture(csv_name),
        "--output", str(output),
        "--symbol", "TESTUSDT",
        "--exchange", "synthetic",
        "--asset-class", "crypto",
        *extra,
    ]


# 1: Default ohne --strategy -> v0.
def test_default_is_v0(tmp_path, capsys):
    out = tmp_path / "report.md"
    rc = main(_args(out))
    assert rc == 0
    captured = capsys.readouterr().out
    assert "strategy: v0 (MidBreakoutStrategy)" in captured
    text = out.read_text(encoding="utf-8")
    assert "MidBreakoutStrategy" in text
    assert "MidBreakoutStrategyV1" not in text
    # v0-Defaults aufgelöst (bestehendes Verhalten).
    assert "lookback_bars=3" in captured
    assert "stop_distance_pct=0.05" in captured


# 2: --strategy v0 verhält sich wie der Default (byte-identischer Report).
def test_explicit_v0_matches_default(tmp_path):
    out_default = tmp_path / "default.md"
    out_v0 = tmp_path / "v0.md"
    assert main(_args(out_default)) == 0
    assert main(_args(out_v0, "--strategy", "v0")) == 0
    assert out_default.read_bytes() == out_v0.read_bytes()


# 3: --strategy v1 -> MidBreakoutStrategyV1 mit v1-Defaults.
def test_v1_uses_v1_defaults(tmp_path, capsys):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v1"))
    assert rc == 0
    captured = capsys.readouterr().out
    assert "strategy: v1 (MidBreakoutStrategyV1)" in captured
    # v1-Defaults aufgelöst.
    assert "lookback_bars=12" in captured
    assert "stop_distance_pct=0.01" in captured
    assert "breakout_threshold_pct=0.001" in captured
    assert "cooldown_bars=3" in captured
    assert "MidBreakoutStrategyV1" in out.read_text(encoding="utf-8")


# 4: --strategy v1 akzeptiert --breakout-threshold-pct.
def test_v1_accepts_breakout_threshold(tmp_path, capsys):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v1", "--breakout-threshold-pct", "0.002"))
    assert rc == 0
    assert "breakout_threshold_pct=0.002" in capsys.readouterr().out


# 5: --strategy v1 akzeptiert --cooldown-bars.
def test_v1_accepts_cooldown_bars(tmp_path, capsys):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v1", "--cooldown-bars", "5"))
    assert rc == 0
    assert "cooldown_bars=5" in capsys.readouterr().out


# 6: --strategy v0 + --breakout-threshold-pct -> abgelehnt, keine Datei.
def test_v0_with_breakout_threshold_rejected(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v0", "--breakout-threshold-pct", "0.001"))
    assert rc != 0
    assert not out.exists()


# 7: --strategy v0 + --cooldown-bars -> abgelehnt, keine Datei.
def test_v0_with_cooldown_rejected(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v0", "--cooldown-bars", "3"))
    assert rc != 0
    assert not out.exists()


# 7b: v1-only Parameter ohne explizites --strategy (Default v0) -> abgelehnt.
def test_v1_only_param_with_default_strategy_rejected(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--cooldown-bars", "3"))
    assert rc != 0
    assert not out.exists()


# 8: ungültige --strategy -> abgelehnt, keine Datei.
def test_invalid_strategy_rejected(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v2"))
    assert rc != 0
    assert not out.exists()


# 9: ungültiger --breakout-threshold-pct (>= 0.1) -> abgelehnt, keine Datei.
def test_invalid_breakout_threshold_rejected(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v1", "--breakout-threshold-pct", "0.2"))
    assert rc != 0
    assert not out.exists()


# 9b: negativer --breakout-threshold-pct -> abgelehnt.
def test_negative_breakout_threshold_rejected(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v1", "--breakout-threshold-pct", "-0.01"))
    assert rc != 0
    assert not out.exists()


# 10: ungültiger --cooldown-bars (< 0) -> abgelehnt, keine Datei.
def test_invalid_cooldown_rejected(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v1", "--cooldown-bars", "-1"))
    assert rc != 0
    assert not out.exists()


# 11: gemeinsame Parameter werden explizit für die gewählte Strategie übernommen.
def test_common_params_override_for_selected_strategy(tmp_path, capsys):
    out = tmp_path / "report.md"
    rc = main(_args(
        out, "--strategy", "v1", "--lookback-bars", "3", "--stop-distance-pct", "0.02",
        "--min-strength", "0.0",
    ))
    assert rc == 0
    captured = capsys.readouterr().out
    assert "lookback_bars=3" in captured
    assert "stop_distance_pct=0.02" in captured


# 12: ungültige --min-strength -> abgelehnt, keine Datei.
def test_invalid_min_strength_rejected(tmp_path):
    out = tmp_path / "report.md"
    rc = main(_args(out, "--strategy", "v1", "--min-strength", "1.5"))
    assert rc != 0
    assert not out.exists()


# 13: Statischer Scan -> CLI-Modul ohne Netzwerk-/Live-/Paper-Trading-Pfade.
def test_cli_module_has_no_forbidden_paths():
    import inspect

    from liquent.cli import backtest_mid_breakout as module

    source_code = inspect.getsource(module).lower()
    forbidden = [
        "soc" + "ket",
        "url" + "lib",
        "req" + "uests",
        "ht" + "tp://",
        "ht" + "tps://",
        "web" + "soc" + "ket",
        "cc" + "xt",
        "live_" + "order",
        "place_" + "order",
        "paper_" + "trading",
        "api_" + "key",
        "sec" + "ret",
    ]
    for token in forbidden:
        assert token not in source_code, f"CLI-Modul darf {token!r} nicht enthalten"
