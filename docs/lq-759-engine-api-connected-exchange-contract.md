# LQ-759 — Engine API Connected Exchange Contract

## Ziel

Für einen extern besessenen, bereits akzeptierten Clientstream wird genau ein
Daemonstream erworben, aktuell verifiziert, für höchstens einen Exchange genutzt
und anschließend deterministisch geschlossen.

## Feste Folge

Die Operation ruft genau einmal den kontrollierten Daemonconnector auf. Der
zurückgegebene Stream wird zusammen mit dem Clientstream ausschließlich an den
Verified Exchange übergeben.

Dieser prüft beide Kernelpeers erneut vor I/O und führt danach höchstens einen
vollständig gegateten Austausch aus.

## Ownership

Der Daemonstream gehört ab erfolgreichem Connect bis zum Operationsende der
Einmaloperation. Er wird nach Erfolg, Exchangefehler oder unerwartetem Fehler
genau einmal geschlossen.

Der Clientstream bleibt immer extern besessen und wird nie geschlossen.

## Fehlersemantik

Scheitert der Connector vor einer Streamrückgabe, gibt es kein Closeziel und der
Exchange wird nicht aufgerufen.

Exchange- und Closefehler werden detailfrei. Ein Closefehler nach fachlich
erfolgreichem Exchange bleibt technische Nichtverfügbarkeit, weil der
Ressourcenabschluss nicht bestätigt ist.

Es gibt keinen Retry nach Connect oder begonnener Exchange-Wirkung.

## Grenzen

Kein Clientlistener, Accept, Loop, Parallelismus, Prozesssignal oder
Production-Wiring wird ergänzt.
