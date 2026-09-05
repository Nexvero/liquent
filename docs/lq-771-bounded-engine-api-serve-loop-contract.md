# LQ-771 — Bounded Engine API Serve Loop Contract

## Ziel

Ein bereits aktiver, extern besessener Listener darf sequenziell eine explizit
begrenzte Anzahl vollständig isolierter Einzelaustausche bedienen.

## Stopprüfung

Vor jedem möglichen `serve_one` wird genau einmal eine externe Stopquelle
gelesen. Nur der echte boolesche Wert `True` beendet den Lauf neutral; `False`
erlaubt genau den nächsten Einzelaustausch.

Fehlende, typfalsche oder fehlschlagende Stopquellen sind technische
Nichtverfügbarkeit und führen zu keiner Acceptwirkung.

Die Stopquelle enthält keine Request- oder Exchangeautorität.

## Harte Grenze

Eine positive feste Maximalzahl begrenzt jeden Lauf unabhängig von der
Stopquelle. Nach genau dieser Zahl endet der Lauf mit `exchange_limit`, ohne
zusätzliche Stopprüfung oder Acceptwirkung.

## Fehlerverhalten

Ein technischer Fehler eines Einzelaustauschs beendet den Lauf sofort. Es gibt
keinen Retry, kein Überspringen und kein Fehlerbudget in diesem Slice.

## Ergebnis

Das unveränderliche Ergebnis enthält ausschließlich die Zahl vollständig
abgeschlossener Einzelaustausche und `stopped` oder `exchange_limit`.

## Grenzen

Der Loop öffnet, schließt oder retired den Listener nicht. Eine blockierende
Acceptoperation kann nur außerhalb dieses Slices durch Listenerclose oder
Prozesssignal unterbrochen werden.

Kein Thread, Signalhandler, Sleep oder Parallelismus wird ergänzt.
