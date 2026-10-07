"""Plain German overview uses stored evidence, never rankings or derived results."""

from copy import deepcopy
from html.parser import HTMLParser

import pytest

from liquent_platform.transport.http.research_results import result_document
from test_research_customer_results import pilot


def overview(evidence):
    document = result_document("job", "succeeded", evidence)
    return document.split('<h2>Kurz erklärt</h2>', 1)[1].split('</section>', 1)[0]


def test_overview_precedes_details_and_preserves_three_ordered_rows_and_values():
    evidence = pilot()
    original = deepcopy(evidence)
    document = result_document("job", "succeeded", evidence)
    plain = overview(evidence)
    assert document.index("Kurz erklärt") < document.index("Variante: Z-first")
    assert plain.index("Z-first") < plain.index("A-second") < plain.index("M-third")
    rows = plain.split('<tbody>', 1)[1].split('</tbody>', 1)[0]
    assert rows.count('<tr>') == 3
    assert rows.index("Z-first") < rows.index("A-second") < rows.index("M-third")
    assert ('<td>Ausgeführt</td><td>2</td><td>15,00</td><td>5,00</td><td>10,00</td>') in rows
    assert "historische Simulationsergebnis" in plain
    assert "keine künftige Profitabilität" in plain
    assert "keine Handelsempfehlung" in plain
    assert "Keine Variante wird bevorzugt" in plain
    assert evidence == original


@pytest.mark.parametrize("net,word,rendered", [
    (10, "positiv (über null)", "10,00"),
    (-.0010047169811320754, "negativ (unter null)", "-0,001005"),
    (0, "null (weder positiv noch negativ)", "0,00"),
    (5e-324, "positiv (über null)", "4,940656e-324"),
    (-1e-7, "negativ (unter null)", "-1,000000e-07"),
])
def test_net_sign_uses_actual_stored_net_not_capital_or_gross(net, word, rendered):
    evidence = pilot()
    first = evidence["pilot_result"]["variants"][0]
    first["evidence"]["cost_totals"]["net_pnl"] = net
    first["summary"].update(starting_equity=1000, ending_equity=999999)
    plain = overview(evidence)
    note = plain.split('<li>', 1)[1].split('</li>', 1)[0]
    assert word in note
    assert f'<td>{rendered}</td>' in plain
    assert "999.999" not in plain


@pytest.mark.parametrize("value", [
    None, True, False, float("nan"), float("inf"), -float("inf"),
    "10", {}, [], 10**1000,
])
@pytest.mark.parametrize("key", ["gross_pnl", "total", "net_pnl"])
def test_invalid_totals_are_visibly_unavailable_and_insufficient(key, value):
    evidence = pilot()
    evidence["pilot_result"]["variants"][0]["evidence"]["cost_totals"][key] = value
    plain = overview(evidence)
    note = plain.split('<li>', 1)[1].split('</li>', 1)[0]
    assert "Evidenz reicht nicht" in note
    row = plain.split('<tbody>', 1)[1].split('</tr>', 1)[0]
    assert "Nicht verfügbar" in row
    if key == "net_pnl":
        assert "Nettoergebnis nicht verfügbar" in note
        assert "Nettoergebnis ist" not in note


@pytest.mark.parametrize("count", [None, True, False, -1, 1.5, "0", {}, float("nan"), float("inf")])
def test_invalid_trade_counts_do_not_become_zero_or_valid_counts(count):
    evidence = pilot()
    evidence["pilot_result"]["variants"][0]["summary"]["number_of_trades"] = count
    plain = overview(evidence)
    note = plain.split('<li>', 1)[1].split('</li>', 1)[0]
    assert "Trade-Anzahl ist nicht verfügbar" in note
    assert "null Trades" not in note
    assert '<td>Ausgeführt</td><td>Nicht verfügbar</td>' in plain
    document = result_document("job", "succeeded", evidence)
    assert '<dt>Simulierte Trades</dt><dd>Nicht verfügbar</dd>' in document


@pytest.mark.parametrize("state,count,expected", [
    ("no_signals", 0, "keine Signale gefunden"),
    ("succeeded", 0, "null Trades simuliert"),
    ("failed", None, "Ausführung ist fehlgeschlagen"),
    ("blocked_data", None, "Datenprüfung hat die Ausführung blockiert"),
    ([], None, "Ausführungsstatus ist nicht verfügbar"),
])
def test_status_and_zero_trades_are_not_success_evidence(state, count, expected):
    evidence = pilot()
    first = evidence["pilot_result"]["variants"][0]
    first.update(status=state, summary={"number_of_trades": count})
    note = overview(evidence).split('<li>', 1)[1].split('</li>', 1)[0]
    assert expected in note
    if count == 0:
        assert "Leistungskennzahlen sind nicht aussagekräftig" in note
    if state in ("failed", "blocked_data"):
        assert "kein belastbares Ergebnis" in note


@pytest.mark.parametrize("summary,stored", [
    (None, None), ({"number_of_trades": 2}, {}),
    ({"starting_equity": 100, "ending_equity": 120, "number_of_trades": 2},
     {"cost_totals": {"gross_pnl": 20, "fee": 1, "spread": 2, "slippage": 3}}),
])
def test_missing_evidence_is_not_reconstructed(summary, stored):
    evidence = pilot()
    evidence["pilot_result"]["variants"][0].update(summary=summary, evidence=stored)
    plain = overview(evidence)
    row = plain.split('<tbody>', 1)[1].split('</tr>', 1)[0]
    assert '<td>Nicht verfügbar</td><td>Nicht verfügbar</td>' in row
    assert "Nettoergebnis nicht verfügbar" in plain
    assert '<td>6,00</td>' not in row and '<td>14,00</td>' not in row


def test_escaping_and_whitelist_in_overview_and_details():
    evidence = pilot()
    first = evidence["pilot_result"]["variants"][0]
    first["variant_id"] = '<img src=x onerror="alert(1)">'
    first["error"] = '<script>alert(1)</script>'
    first["summary"]["private_token"] = "do-not-render"
    first["evidence"]["cost_totals"]["net_pnl"] = '<svg onload="alert(1)">'
    document = result_document("job", "succeeded", evidence)
    assert '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;' in overview(evidence)
    assert "&lt;script&gt;" in document
    for unsafe in ('<img src=x', '<script>', '<svg', 'do-not-render'):
        assert unsafe not in document


@pytest.mark.parametrize("variants", [None, {}, [], [{}], [None] * 3, [{}] * 4])
def test_invalid_variant_structure_has_no_overview(variants):
    evidence = pilot()
    evidence["pilot_result"]["variants"] = variants
    document = result_document("job", "succeeded", evidence)
    assert "Varianten-Evidenz unvollständig" in document
    assert "Kurz erklärt" not in document


class DetailVisibility(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.visible = []
        self.collapsed = []

    def handle_starttag(self, tag, attrs):
        if tag == "details":
            assert "open" not in dict(attrs)
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "details":
            self.depth -= 1
            assert self.depth >= 0

    def handle_data(self, data):
        (self.collapsed if self.depth else self.visible).append(data)


def test_only_technical_inputs_collapsed_limits_results_and_risk_stay_visible():
    parser = DetailVisibility()
    parser.feed(result_document("job", "succeeded", pilot()))
    assert parser.depth == 0
    hidden, visible = ''.join(parser.collapsed), ''.join(parser.visible)
    for label in ("Eingabebindung", "Vereinbarte Eingaben", "Vereinbarte Strategieparameter",
                  "Tatsächlich gespeicherte Laufparameter", "Kostenannahmen"):
        assert label in hidden
        assert label not in visible
    for label in ("Kurz erklärt", "Verbindliche Modellgrenzen", "keine tatsächliche Stop-Loss-Ausführung",
                  "Gespeicherte Risikowirkung", "Tatsächliches simuliertes Ergebnis und Kosten",
                  "Synthetic failure"):
        assert label in visible
