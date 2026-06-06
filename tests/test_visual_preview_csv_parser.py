"""Tests für den lokalen CSV-Textparser der Visual Preview (LQ-022 Phase 2).

CSV-Inhalte ausschließlich als String — keine echten CSV-Dateien, keine
tmp-Dateien, kein pandas, kein Netzwerk, kein File-I/O.
"""

from datetime import timezone

from tools.visual_preview.preview_logic import (
    CSV_REQUIRED_COLUMNS,
    PreviewDataset,
    SAMPLE_CSV_TEMPLATE,
    build_dataset_from_csv_text,
    generate_preview_summary,
)


def _error_message(fn) -> str:
    try:
        fn()
    except ValueError as exc:
        return str(exc)
    raise AssertionError("erwartete ValueError wurde nicht ausgelöst")

_VALID = (
    "timestamp,bid,ask,volume\n"
    "2026-01-01T00:00:00+00:00,100.0,100.5,1.0\n"
    "2026-01-01T00:05:00+00:00,100.2,100.7,2.0\n"
)


def _expect_value_error(fn) -> None:
    raised = False
    try:
        fn()
    except ValueError:
        raised = True
    assert raised, "erwartete ValueError wurde nicht ausgelöst"


# 1: gültige CSV -> PreviewDataset.
def test_valid_csv_builds_dataset():
    ds = build_dataset_from_csv_text("up.csv", _VALID)
    assert isinstance(ds, PreviewDataset)
    assert ds.name == "up.csv"
    assert ds.description == "Local CSV preview dataset"
    assert len(ds.market_data) == 2
    bar = ds.market_data[0]
    assert bar.timestamp.tzinfo == timezone.utc
    assert bar.bid == 100.0 and bar.ask == 100.5 and bar.volume == 1.0


# 2: ohne volume -> Default 1.0.
def test_missing_volume_defaults_to_one():
    csv_text = "timestamp,bid,ask\n2026-01-01T00:00:00+00:00,10.0,11.0\n"
    ds = build_dataset_from_csv_text("x", csv_text)
    assert ds.market_data[0].volume == 1.0


# 2b: leeres volume-Feld -> Default 1.0.
def test_empty_volume_field_defaults_to_one():
    csv_text = "timestamp,bid,ask,volume\n2026-01-01T00:00:00+00:00,10.0,11.0,\n"
    ds = build_dataset_from_csv_text("x", csv_text)
    assert ds.market_data[0].volume == 1.0


# 3: CSV ohne Datenzeilen -> abgelehnt.
def test_header_only_rejected():
    _expect_value_error(lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n"))


# 4: leere CSV -> abgelehnt.
def test_empty_csv_rejected():
    _expect_value_error(lambda: build_dataset_from_csv_text("x", ""))


# 5: fehlende Pflichtspalte -> abgelehnt.
def test_missing_required_column_rejected():
    _expect_value_error(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid\n2026-01-01T00:00:00+00:00,10\n")
    )


# 6/7: nicht-numerisches bid/ask -> abgelehnt.
def test_non_numeric_bid_ask_rejected():
    _expect_value_error(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n2026-01-01T00:00:00+00:00,abc,11\n")
    )
    _expect_value_error(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n2026-01-01T00:00:00+00:00,10,xyz\n")
    )


# 8: bid <= 0 -> abgelehnt.
def test_nonpositive_bid_rejected():
    _expect_value_error(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n2026-01-01T00:00:00+00:00,0,11\n")
    )


# 9: ask < bid -> abgelehnt.
def test_ask_below_bid_rejected():
    _expect_value_error(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n2026-01-01T00:00:00+00:00,12,11\n")
    )


# 10: naiver timestamp -> abgelehnt.
def test_naive_timestamp_rejected():
    _expect_value_error(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n2026-01-01T00:00:00,10,11\n")
    )


# 11: unparsebarer timestamp -> abgelehnt.
def test_unparseable_timestamp_rejected():
    _expect_value_error(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\nnot-a-date,10,11\n")
    )


# 12: unsortierte CSV wird nach timestamp sortiert.
def test_unsorted_csv_is_sorted():
    csv_text = (
        "timestamp,bid,ask\n"
        "2026-01-01T00:10:00+00:00,10,11\n"
        "2026-01-01T00:00:00+00:00,10,11\n"
        "2026-01-01T00:05:00+00:00,10,11\n"
    )
    ds = build_dataset_from_csv_text("x", csv_text)
    ts = [b.timestamp.isoformat() for b in ds.market_data]
    assert ts == [
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:05:00+00:00",
        "2026-01-01T00:10:00+00:00",
    ]


# 13: mids werden korrekt berechnet ((bid+ask)/2).
def test_mids_are_correct():
    ds = build_dataset_from_csv_text("x", _VALID)
    assert ds.mids == (100.25, 100.45)
    for bar, mid in zip(ds.market_data, ds.mids):
        assert (bar.bid + bar.ask) / 2.0 == mid


# 14: generate_preview_summary funktioniert mit CSV-Dataset.
def test_summary_works_with_csv_dataset():
    ds = build_dataset_from_csv_text("up.csv", _VALID)
    summary = generate_preview_summary(ds, "v1", {})
    assert summary["dataset"]["name"] == "up.csv"
    assert summary["dataset"]["type"] == "synthetic"  # Preview-Kontext, nicht echt
    assert summary["technical_summary"]["bars"] == 2
    assert isinstance(summary["signals_total"], int)
    assert "chart_rows" in summary and "price_rows" in summary


# 15: Parser ist rein (keine I/O) — gleicher Input liefert gleiches Ergebnis.
def test_parser_is_pure_and_deterministic():
    a = build_dataset_from_csv_text("x", _VALID)
    b = build_dataset_from_csv_text("x", _VALID)
    assert a == b


# --------------------------------------------------------------------------- #
# LQ-023: Sample-Template + nutzerfreundliche, row-nummerierte Fehlermeldungen
# --------------------------------------------------------------------------- #


# 16: SAMPLE_CSV_TEMPLATE ist parsebar und ergibt >= 3 Bars.
def test_sample_template_is_parseable():
    ds = build_dataset_from_csv_text("sample", SAMPLE_CSV_TEMPLATE)
    assert len(ds.market_data) >= 3


# 17: CSV_REQUIRED_COLUMNS ist die erwartete Pflichtspalten-Liste.
def test_required_columns_constant():
    assert CSV_REQUIRED_COLUMNS == ("timestamp", "bid", "ask")


# 18: fehlende Pflichtspalte nennt die konkrete Spalte.
def test_missing_column_names_the_column():
    msg = _error_message(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid\n2026-01-01T00:00:00+00:00,10\n")
    )
    assert "missing required column" in msg
    assert "ask" in msg


# 19: ungültiger timestamp -> Row-Hinweis + ISO-8601.
def test_invalid_timestamp_message():
    msg = _error_message(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\nnope,10,11\n")
    )
    assert "CSV row 2" in msg
    assert "ISO-8601" in msg


# 20: naiver timestamp -> Hinweis auf timezone.
def test_naive_timestamp_message():
    msg = _error_message(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n2026-01-01T00:00:00,10,11\n")
    )
    assert "CSV row 2" in msg
    assert "timezone information" in msg


# 21: ungültiger bid -> "positive number".
def test_invalid_bid_message():
    msg = _error_message(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n2026-01-01T00:00:00+00:00,abc,11\n")
    )
    assert "bid must be a positive number" in msg


# 22: ask < bid -> "greater than or equal".
def test_ask_below_bid_message():
    msg = _error_message(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask\n2026-01-01T00:00:00+00:00,12,11\n")
    )
    assert "greater than or equal to bid" in msg


# 23: ungültige volume -> "numeric".
def test_invalid_volume_message():
    msg = _error_message(
        lambda: build_dataset_from_csv_text("x", "timestamp,bid,ask,volume\n2026-01-01T00:00:00+00:00,10,11,xx\n")
    )
    assert "volume must be numeric" in msg


# 24: Fehlermeldungen enthalten keine Traceback-Details.
def test_messages_have_no_traceback_details():
    samples = [
        "",
        "timestamp,bid\n2026-01-01T00:00:00+00:00,10\n",
        "timestamp,bid,ask\nnope,10,11\n",
        "timestamp,bid,ask\n2026-01-01T00:00:00+00:00,12,11\n",
    ]
    for text in samples:
        msg = _error_message(lambda t=text: build_dataset_from_csv_text("x", t))
        assert "Traceback" not in msg
        assert 'File "' not in msg
