# LQ-712 — Engine API Proxy Route Policy

## Umsetzung

`ClosedManifestHandoffSupervisorEngineApiRoutePolicy` ist eine reine,
I/O-freie Klassifikationsgrenze.

Sie akzeptiert Methode, Requesttarget und optionalen Body und liefert nur einen
typisierten Operationsfakt zurück.

## Find

Find verlangt GET, keinen Body, `all=1` und genau einen kanonisch kodierten
`liquent.supervisor.creation`-Filter.

Der Creationwert ist begrenzt und enthält nur die geschlossene ID-Zeichenmenge.

## Containeroperationen

Inspect, Start, Wait, Stop und Kill verlangen eine lowercase hexadezimale
64-Zeichen-ID und ihre jeweils exakte Method-/Query-/Bodyform.

## Create

Create verlangt POST, keinen Querystring und einen nichtleeren begrenzten Body.

Der Rückgabefakt bedeutet ausschließlich Routenklassifikation. Die Policy besitzt
keine `forward`-, `connect`- oder `listen`-Oberfläche.

## Fehlergrenze

Parsing-, Unicode-, Größen-, Methoden-, Pfad- und Queryfehler werden an der
bestehenden technischen Grenze detailfrei vereinheitlicht.
