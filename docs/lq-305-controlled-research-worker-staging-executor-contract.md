# LQ-305 — Controlled Research Worker Staging Executor Contract

## Zweck

LQ-305 definiert den beobachtbaren Vertrag eines späteren kontrollierten
Research-Worker-Staging-Executors.

Der Executor erhebt redigierte Evidence für die 29 LQ-303-Gates. Er entscheidet
kein `approved`, `rejected` oder `unavailable`; diese Entscheidung bleibt
ausschließlich beim unabhängigen LQ-304-Verifier.

Dieser Slice implementiert und startet noch keinen Executor, Container,
Stagingdienst oder Datenbankzugriff.

## Explizite Autorisierung

Ein Lauf verlangt eine separate owner-only Autorisierungsdatei für genau einen
Staginglauf.

Sie bindet opake Run-ID, Environment exakt `staging`, Source-Commit,
unveränderlichen Application-Image-Digest, Compose-SHA-256, erwarteten
Migration-Head, Executor-Identität, Autorisierer-Identität sowie ein enges
UTC-Zeitfenster.

Executor und Autorisierer müssen verschieden sein. Die Autorisierung ist keine
Produktrolle, Membership, Capability oder Researchpermission.

Production, Wildcards, mutable Tags, offene Zeitfenster, wiederverwendete
Run-IDs und caller-gelieferte Allow-Booleans sind unzulässig.

Die Autorisierung erlaubt ausschließlich die im Vertrag benannten
Stagingoperationen. Sie erlaubt kein Productiondeployment, kein Package-
Publishing, keine reguläre Identity-/Workspace-/Membership-Erzeugung und keine
Tradingverbindung.

## Kontrollierte Inputs

Der spätere Command erhält ausschließlich absolute Pfade zu:

- owner-only Run-Autorisierung;
- geprüftem Composefile;
- owner-only Compose-Environmentdatei;
- owner-only Image-Environmentdatei;
- owner-only Worker-Konfiguration und Worker-ID;
- owner-only Datenbank-URL-Datei;
- read-only synthetischem Research-Dataset;
- leerem owner-kontrolliertem Evidence-Ausgabeverzeichnis.

Dateiinhalte werden nie als CLI-Werte oder Environmentfallbacks akzeptiert.
Symlinks, Hardlinks, fremder Owner, breite Modi, nicht absolute Pfade,
unbekannte Dateien und nicht leere Outputverzeichnisse scheitern vor Docker-
oder Datenbankzugriff.

## Vorbereitungsphase

Vor jeder Mutation prüft der Executor lokal:

1. Autorisierungsstruktur, Zeitfenster und getrennte Identitäten;
2. Source-Commit und Compose-SHA-256;
3. alle Imagewerte auf immutable SHA-256-Referenzen;
4. Worker-Konfiguration auf feste LQ-301-Containerpfade, Konkurrenz eins und
   deaktiviertes Trading;
5. Datasetregularität und vorab gebundenen SHA-256;
6. leeres privates Evidenceziel;
7. vorhandene Docker-Compose-Fähigkeit ohne Shellinterpolation.

Jeder Fehler endet vor Pull, Compose-Render, Migration oder Containerstart.

## Ausführungsphasen

Ein autorisierter Lauf besitzt eine feste monotone Reihenfolge:

1. Image-Digest auflösen und Revision/Runtimeidentität inspizieren;
2. Compose ausschließlich mit den gebundenen Dateien rendern;
3. effektive Mount-, Secret-, Netzwerk-, Port- und Grace-Grenzen prüfen;
4. nur die gebundene isolierte Staging-PostgreSQL-Instanz bereitstellen;
5. Migration-Gate einmal ausführen und exakten Head read-only prüfen;
6. genau einen Worker starten und den mutationsfreien Idle-Pfad beobachten;
7. einen synthetischen Job autorisiert annehmen und terminal beobachten;
8. Artifacthash und genau-ein-Claim/-Outcome prüfen;
9. Permission entziehen und den vorbereiteten zweiten Job fail-closed prüfen;
10. Idle-SIGTERM und nach Neustart Running-SIGTERM kontrolliert prüfen;
11. Worker stoppen und redigierte Evidence atomar finalisieren.

Phasen dürfen nicht übersprungen, umgeordnet, parallelisiert oder nach einem
unbekannten Effekt automatisch wiederholt werden.

## Mutationsbudget

Der Executor darf nur innerhalb der gebundenen isolierten Staginggrenze:

- die exakt gebundenen Images pullen;
- die dedizierten Compose-Ressourcen dieses Runs erstellen und starten;
- Migrationen bis zum bereits erwarteten Head anwenden;
- fest benannte synthetische Testfakten über bestehende autorisierte Grenzen
  erzeugen;
- genau die vorgesehene Researchpermission für den synthetischen Actor
  entziehen;
- dedizierte Probe- und Run-Ressourcen kontrolliert stoppen.

Er darf keine bestehende Datenbank, kein Volume, Netzwerk, Image, Artifact oder
Evidenceobjekt löschen oder überschreiben. Cleanup ist ein eigener späterer
Vertrag und kein impliziter Erfolgsschritt.

## Fehler- und Stopsemantik

Vor Mutation ist jeder Fehler sicher wiederholbar. Nach dem ersten möglichen
externen Effekt wird derselbe Run niemals automatisch erneut gestartet.

Timeout, Dockerverlust, Outputverlust, unbekannter Containerstatus,
Datenbankunterbrechung oder SIGTERM-Unklarheit ergeben einen Unknown Outcome.
Der Executor stoppt weitere Phasen und schreibt nur vorhandene redigierte
Evidence plus fehlende Checks als `unavailable`.

Ein explizit beobachteter Invariantenbruch wird als `failed` erfasst. Der
Executor übersetzt ihn nicht selbst in `rejected`.

SIGINT oder SIGTERM an den Executor fordert nur kontrollierten Stopp an. Ein
laufender Unterprozess erhält keine zweite Signalfolge; SIGKILL wird nicht als
erfolgreiche Evidence gewertet.

## Evidence-Ausgabe

Der Executor schreibt ein geschlossenes LQ-304-kompatibles JSON-Dokument erst
in eine neue temporäre Datei im Evidenceverzeichnis.

Jedes ausgeführte Gate erhält Status, opake Evidence-Referenz und SHA-256 eines
separaten redigierten Evidenzobjekts. Nicht erreichte Gates werden mit Status
`unavailable` und beiden Nachweisfeldern `null` finalisiert.

Nach vollständigem Fsync wird das JSON atomar unter einem festen Runnamen
verlinkt. Bestehende Ziele werden niemals ersetzt.

Raw stdout/stderr, Compose-Environmentdateien, DSNs, Secrets, Hostpfade,
Container-Inspect-Dumps, SQL-Zeilen, Job-/Claim-IDs und Artifactinhalte werden
nicht in Evidence übernommen.

## Redaction und Prozessausführung

Unterprozesse werden ausschließlich als feste Argumentlisten ohne Shell
gestartet. Environment wird geschlossen allowlisted; Proxy-, Credential-,
Pythonpath- und Docker-Overridevariablen werden nicht geerbt.

Commandausgaben werden begrenzt im Speicher geprüft und sofort auf erlaubte
neutrale Fakten reduziert. Unbegrenzte Pipes, Debugtracing und persistente
Rohlogs sind verboten.

Kein Fehlertext eines Unterprozesses verlässt die Executorgrenze.

## Trennung der Entscheidungen

Der Executor darf LQ-304 weder importieren noch automatisch aufrufen.

Ein anderer Actor übergibt die atomar finalisierte Evidence später separat an
`liquent-research-worker-staging-evidence`.

Executor-Erfolg bedeutet nur, dass ein vollständiger Datensatz geschrieben
wurde. Er ist keine Readinessentscheidung und keine Deploymentfreigabe.

## Nichtziele

LQ-305 entscheidet keine konkrete Dockerbibliothek, Subprocess-API,
Timeoutwerte, Dateinamen, Evidenceobjektformate unterhalb ihrer Hashreferenz,
SQL-Abfragen oder Staging-Providerintegration.

Es gibt keine Schema-, Tabellen-, Migration-, Port-, Domainmodell-,
Produkt-CLI- oder Composeänderung.

Es gibt keinen realen Imagepull, Containerstart, Datenbankzugriff, Joblauf,
Permissionentzug oder Signalversand in diesem Slice.

## Implementierungsfolge

LQ-306 sollte den owner-kontrollierten Executor gemäß diesem Vertrag
implementieren und vollständig über injizierte Prozess-, Clock- und
Dateigrenzen testen.

Ein echter Staginglauf bleibt danach weiterhin eine separate, ausdrücklich
autorisierte Operation und darf in einer lokalen Testsuite nicht simuliert als
erfolgreich ausgegeben werden.
