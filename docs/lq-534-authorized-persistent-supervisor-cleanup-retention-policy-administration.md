# LQ-534 — Authorized Persistent Supervisor Cleanup Retention Policy Administration

## Ergebnis

LQ-534 erweitert den LQ-533-Adapter um reguläre erwartungsgebundene
Policy-Ersetzung und kontrollierte Deaktivierung.

Jede Mutation prüft aktuelle Authority, Actorstatus und Policyprojektion in
derselben Datenbanktransaktion.

## Actor ist keine Authority

`SessionPrincipal` liefert ausschließlich die persistente Actor-User-ID.

Der Adapter akzeptiert keinen Allowboolean, keine Rolle und keine Permission.

Er liest die aktuelle Retention-Policy-Authority-Menge und den aktuellen
Userstatus direkt aus dem System of Record.

Nur ein aktiver Member mit weiterhin aktivem Userfact darf mutieren.

Membership und die vier Cleanup-Source-Authorities bleiben getrennt.

## Retry zuerst

Vor Authority-, Erwartungs-, Clock- oder Generatorprüfung sucht der Adapter die
immutable Change-ID.

Ein Retry mit identischem Actor, Intent, erwarteter Revision und Dauer
rekonstruiert das historische Resultat.

Er erzeugt keine neue Revision und reaktiviert keine alte Projektion.

Abweichende Wiederverwendung derselben Change-ID liefert detailfreien Conflict.

Ein erfolgreicher historischer Retry bleibt auch nach späterem Entzug lesbar;
er ist keine neue autorisierte Wirkung.

## Erwartungsbindung

Die erwartete Revision muss exakt der aktuell aktiven Policyrevision
entsprechen.

Bei fehlender aktiver Policy ist ausschließlich die geschlossene Erwartung
`None` für einen Replace zulässig.

Eine Erwartung ist niemals Wildcard oder Ignorewert.

Stale, fehlende oder widersprüchliche Erwartungen liefern detailfreien
Conflict und erzeugen keine Revision.

## Replace

Replace verlangt eine positive sekundengenaue Dauer aus dem Domaincommand.

Die neue Policyrevision-ID wird intern erzeugt und typgeprüft.

Eine bereits persistierte generierte Revision-ID wird detailfrei abgelehnt.

Revision, Changefact und aktive Projektion werden atomar geschrieben.

Die vorherige Revision bleibt immutable historisch erhalten.

Es gibt keinen Zwischenzustand mit partiell aktiver neuer Policy.

## Keine Verkürzung

Die neue Dauer muss mindestens so groß wie die höchste bisher persistierte
Policydauer sein.

Da reguläre Revisionen monoton sind, entspricht dies der letzten zulässigen
Untergrenze auch nach einer Deaktivierung.

Gleiche oder längere Dauer ist erlaubt.

Eine Verkürzung liefert detailfreien Conflict vor Revisiongenerator und Clock.

Damit kann reguläre Administration Cleanup nicht beschleunigen.

## Deaktivierung

Deactivate verlangt eine aktuell aktive und exakt erwartete Revision.

Der Command darf keine Dauer tragen und erzeugt keine neue Policyrevision.

Die aktuelle Projektion wird entfernt und ein immutable Changefact mit leerem
Resultat geschrieben.

Keine frühere Policyrevision wird still reaktiviert.

Der nächste aktive Policylookup liefert neutral `None`.

## Widerruf

Authority wird innerhalb jeder neuen Mutation frisch gelesen.

Ein committierter inactive Member oder inactive Userfact sperrt jede spätere
neue Änderung fail-closed.

Ein zuvor separat ermitteltes Permit wird weder angenommen noch gecacht.

## Zeitmonotonie

Die vertrauenswürdige Clock wird erst nach allen fachlichen Vorprüfungen
gelesen.

Replace darf nicht vor der neuesten Policyerzeugungszeit liegen.

Deactivate darf nicht vor der aktuell aktiven Revision liegen.

Regressierende oder beschädigte Zeiten sind technische Nichtverfügbarkeit.

## Serialisierung

PostgreSQL sperrt User-, Policy-, Aktivierungs-, Authority-, Bootstrap- und
Changetabellen in fester Reihenfolge unter einer Write-Transaktion.

Dadurch teilen Authorityprüfung, Erwartungsprüfung und Projektion denselben
serialisierten System-of-Record-Zustand.

SQLite bleibt nur lokale Testgrenze.

## Fehlergrenzen

Fehlende aktuelle Authority liefert neutral `None` und keine Wirkung.

Stale Erwartungen, Wiederverwendung, Verkürzung und ID-Kollision liefern den
bestehenden feldlosen fachlichen Conflict.

Beschädigte Persistenz, Clock-, Generator-, Dialekt- oder Infrastrukturfehler
bleiben bestehende detailfreie `ManifestHandoffRegistryUnavailable`.

Es entsteht kein neuer Exceptiontyp.

## Bewusst nicht enthalten

Keine Authority-Grants, Deaktivierungen oder Reaktivierungen.

Keine Offline-Recovery oder Ausnahmeverkürzung.

Keine Evaluation, Clearance, Decision, Operation oder Dateiwirkung.

Keine Migration, CLI, Route, Composition, Konfiguration oder Productionwiring.

## Bestand

Der Bestand bleibt bei 63 Entry Points, 68 Operatormodulen und 42 linearen
Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-535 implementiert den persistenten erwartungsgebundenen Authority-Lifecycle
mit vollständigen neuen Set-Revisionen und Lockoutschutz.

Offline-Recovery bleibt danach separat.
