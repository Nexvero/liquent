# LQ-699 — Controlled Supervisor Entrypoint Composition Contract

## Ziel

Der reale Control-Plane-Entrypoint darf die vollständige Supervisorgruppe in
genau eine Engine, Backendidentität, Processcomposition und Factoryübergabe
übersetzen.

## Backendidentität

Die Backendinstanz-ID ist ein stabiler, operatorgebundener Settingsfakt.

Sie wird weder zufällig pro Start erzeugt noch aus Request-, Prozess- oder
Datenbankzustand erraten und darf nicht wiederverwendet werden.

Der geschlossene Wert ist 1 bis 64 Zeichen lang und enthält nur
kleingeschriebene Buchstaben, Ziffern und Bindestriche.

## Engine

Bei aktiven Supervisor-Settings erzeugt der Entrypoint genau eine Engine aus
dem bestehenden Datenbanksecret.

Dieselbe Objektinstanz wird an Processcomposition und Appfactory übergeben.

Die Factory übernimmt sie nur mit einem expliziten Ownershipmarker.

## Übergabe

Der Entrypoint komponiert Prozess und objektidentischen Probe und übergibt
Prozess, Probe, Prozessownership, Engine und Engineownership gemeinsam.

Geschlossene Supervisor-Settings erhalten den bisherigen Entrypointpfad
unverändert.

## Fehlercleanup

Scheitert Processcomposition, wird nur die bereits erzeugte Engine disponiert.

Scheitert die Factory, werden Prozess und Engine geschlossen; bei OIDC zusätzlich
der bereits erzeugte HTTP-Client.

Nach erfolgreicher Factoryübergabe besitzt ausschließlich der App-Lifespan die
Ressourcen.

## Productionstatus

Compose liefert weiterhin weder Socket noch Controlwurzel. Der Probe bleibt
not-ready und `production_ready=false`.
