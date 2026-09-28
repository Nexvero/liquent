# LQ-533 — Persistent Supervisor Cleanup Retention Policy Bootstrap and Current Lookups

## Ergebnis

LQ-533 implementiert auf Revision 0042 den atomaren initialen Bootstrap, den
aktuellen aktiven Policylookup und die aktuelle Authority-Permitauflösung.

Der Slice implementiert keine reguläre Policy- oder Authoritymutation und
keine Recovery.

## Ein Adapter, drei geschlossene Wirkungen

`DatabaseManifestHandoffSupervisorCleanupRetentionPolicy` stellt genau die
jetzt benötigten Methoden aus den LQ-531-Grenzen bereit.

Er nimmt eine extern besessene SQLAlchemy-Engine, eine explizite Clock und zwei
getrennte Revisiongeneratoren entgegen.

Aufbau führt weder Datenbankzugriff noch Clock- oder Generatoraufruf aus.

Die Repräsentation legt keine Engine, IDs oder Policywerte offen.

## Atomarer Bootstrap

Bootstrap validiert ausschließlich den geschlossenen LQ-531-Command.

Unter einer Transaktion entstehen immutable Policyrevision, initiale
Authorityrevision, aktiver Authoritymember, beide aktuellen Projektionen und
der Bootstrapfact.

Der Ziel-User muss im System of Record existieren und aktuell aktiv sein.

Bootstrap erzeugt oder reaktiviert keinen User und keine Membership.

Policy- und Authorityrevision werden intern getrennt erzeugt und typgeprüft.

Beide dürfen nicht denselben Rohwert verwenden.

Clock, Revisionen und Inserts liegen innerhalb derselben Write-Transaktion.

Ein Fehler kann deshalb keinen partiellen initialen Bestand committen.

## Leere Foundation

Ein neuer Bootstrap ist nur möglich, wenn Policy-, Authority-, aktuelle
Projektions- und Bootstrapbestände vollständig leer sind.

Vorhandener fremder Bestand führt neutral zu `None`.

Der Adapter übernimmt keinen beschädigten oder partiellen Bestand.

PostgreSQL serialisiert die Prüfung durch eine feste Tabellensperrreihenfolge.

SQLite bleibt ausschließlich unterstützte lokale Testgrenze.

## Retry und ID-Nichtwiederverwendung

Der Adapter prüft zuerst einen vorhandenen Bootstrap mit derselben ID.

Stimmen Ziel, Datenklasse und Dauer exakt überein, rekonstruiert er dasselbe
persistierte Resultat ohne neue Clock- oder Generatorwerte.

Abweichende Wiederverwendung derselben ID liefert den feldlosen detailfreien
Conflict.

Ein Retry ist kein zweiter Bootstrap und verändert keine Projektion.

## Aktiver Policylookup

Jeder Aufruf liest die aktuelle Singletonprojektion und ihre immutable
Policyrevision frisch aus der Datenbank.

Fehlt die Projektion, liefert der Lookup neutral `None`.

Revision-ID, positive ganzzahlige Sekunden sowie Erzeugungs- und
Aktivierungszeit werden erneut durch die Domainwerte validiert.

Es gibt keinen Cache, Fallback und keine Defaultdauer.

Eine spätere Deaktivierung oder Ersetzung wirkt daher auf den nächsten Lookup.

## Aktuelle Authority-Auflösung

Permit akzeptiert nur einen echten `SessionPrincipal` als Actoridentität.

Der boolesche Wert wird intern aus aktueller Authorityprojektion,
vollständigem Memberfact und aktuellem Userstatus bestimmt.

Nur gleichzeitig aktiver Member und aktiver persistenter User ergeben `True`.

Fehlende Projektion, fehlender Member, inactive Member oder inactive User
ergeben fail-closed `False`.

Der Caller liefert weder Allowboolean, Rolle, Permission noch Authorityrevision.

Jeder Aufruf liest aktuell; ein committierter Entzug sperrt spätere Permits.

## Rekonstruktion

Bootstrap-Retry rekonstruiert Policy und vollständige Authoritymenge getrennt.

Leere, doppelte, unbekannte oder vollständig inaktive Authoritywerte können
nicht als erfolgreiches Domainresultat passieren.

Die persistierte positive Sequenz wird geprüft, aber nicht öffentlich gemacht.

## Fehlergrenze

Erwartete Abwesenheit und inaktive Authority bleiben neutrale Ergebnisse.

ID-Wiederverwendung mit anderem Inhalt bleibt detailfreier fachlicher Conflict.

Beschädigte Persistenz, nicht unterstützte Dialekte, Generatorfehler und
Infrastrukturfehler werden über die bestehende detailfreie
`ManifestHandoffRegistryUnavailable`-Grenze vereinheitlicht.

LQ-533 führt keinen neuen Exceptiontyp ein.

## Bewusst nicht enthalten

Keine reguläre Policyänderung, Deaktivierung oder monotone Dauerprüfung.

Keine Authority-Grants, Deaktivierungen, Reaktivierungen oder Recovery.

Keine Evaluation, Clearance, Decision, Operation oder Dateiwirkung.

Keine Migration, CLI, Route, Composition, Konfiguration oder Productionwiring.

Keine neuen Ports, Domainwerte oder Signaturen.

## Bestand

Der Bestand bleibt bei 63 Entry Points, 68 Operatormodulen und 42 linearen
Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-534 implementiert die erwartungsgebundene reguläre Policyadministration mit
aktueller Authorityprüfung, Nichtverkürzung und atomarer Projektion.

Authority-Lifecycle und Offline-Recovery bleiben danach separat.
