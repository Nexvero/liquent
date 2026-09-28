# LQ-684 — Supervisor Production Ownership, Readiness and Shutdown Evidence

## Ergebnis

Statische Evidenz verfolgt die spätere Auswahl durch Settings, Entrypoint,
Appfactory, Lifecycle und Deployment als eine unteilbare Kette.

## Aktueller Settingsstand

`PlatformSettings` besitzt keine Supervisorauswahl und keine kontrollierten
Docker-Socket-, Control-Root- oder Wrapperidentitätswerte.

Unbekannte Environmentwerte werden weiterhin fail-fast abgewiesen.

Damit kann derzeit keine scheinbar erfolgreiche Settings-only-Aktivierung
stattfinden.

## Entrypoint und Appfactory

Der Production-Entrypoint komponiert weder Kandidat noch Docker-Client.

Die Appfactory übernimmt keinen Supervisorgrafen, keinen Supervisor-Healthprobe
und keinen besessenen Supervisorclient.

Ihr Lifecycle schließt ausschließlich bereits ausdrücklich besessenen
OIDC-Client und App-Datenbank-Engine.

## Deployment

Der Control-Plane-Service besitzt weder Docker-Socket noch Control-Directory-
Hostwurzel.

Compose startet keinen separaten Wrapperdienst und behauptet keine
Supervisorreadiness.

Die vorhandenen installierbaren Wrappercommands sind daher Paketfähigkeit,
nicht Deploymentaktivierung.

## Kandidat und Kompatibilitätsgraph

Der Kandidat bleibt unveränderlich `production_ready=false`.

Der ältere Servicegraph fordert weiterhin Parent-Executor und Parent-Outcomes;
er wird durch den Kandidaten nicht implizit ersetzt.

Diese Trennung belegt, dass noch keine gemischte Laufzeitcomposition besteht.

## Fail-closed Wirkung

Solange irgendein Glied der Auswahlkette fehlt, bleibt der Kandidat ungewählt.

Technische Unverfügbarkeit bleibt detailfrei. Es wird kein neuer Exceptiontyp
benannt und kein Fallback aktiviert.
