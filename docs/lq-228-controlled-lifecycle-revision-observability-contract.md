# LQ-228 — Controlled Lifecycle Revision Observability Contract

## 1. Ergebnis

LQ-228 entscheidet die kleinste sichere Schließung des in LQ-227 gefundenen
operativen Übergabeblockers.

Der bestehende owner-only Identity-Bootstrap soll in seinem erfolgreichen
Resultat zusätzlich genau die beiden Lifecycle-Revisionen ausgeben, die er
atomar mit dem ersten Nutzer und Workspace erzeugt hat.

Es entsteht kein allgemeiner Inspect-, List-, Dump- oder Current-State-
Operator. Reguläre Lifecycle-Mutationen behalten ihre exakte
`expected_revision`-Pflicht.

Dieser Slice ist ausschließlich ein beobachtbarer Vertrag. Er implementiert
noch keine Modell-, Port-, Adapter-, Operator- oder Teständerung.

## 2. Warum die Bootstrap-Grenze zuständig ist

Der Identity-Bootstrap erzeugt in einer Transaktion:

- erste UserId;
- erste WorkspaceId;
- beide initialen Lifecycle-Authorities;
- vollständige initiale Nutzerrevision;
- vollständige initiale Workspace-Revision;
- beide Current-Pointer.

Damit ist er die einzige Grenze, die alle vier für den nächsten regulären
Schritt erforderlichen IDs bereits sicher und atomar kennt.

Eine separate breite Bestandsinspektion wäre für diesen Übergang unnötig.

## 3. Exaktes erfolgreiches Resultat

Ein erfolgreiches `liquent-initial-bootstrap identity` erzeugt eine exklusive
owner-only JSON-Datei mit genau:

- `user_id`;
- `workspace_id`;
- `user_revision_id`;
- `workspace_revision_id`.

Alle vier Werte sind nichtleere opake interne IDs. Es gibt keine weiteren
Felder, Statuswerte, Authority-Aussagen, Rollen oder Counts.

Die beiden Revisionswerte bezeichnen die beim Bootstrap-Commit vollständigen
initialen Nutzer- und Workspacebestände.

## 4. Keine Authority durch Beobachtung

Eine Revisions-ID ist weder Credential noch Capability noch Allow-Entscheid.

Ihr Besitz autorisiert keine Mutation. Jeder spätere User- oder Workspace-
Lifecycle-Create muss weiterhin aktuellen aktiven Actor und die exakt passende
dedizierte Authority aus dem System of Record auflösen.

Eine inzwischen veraltete Revision kann lediglich neutral scheitern. Sie
gewährt keine Fortgeltung früherer Authority.

## 5. Frischer Bootstrap-Erfolg

Beim frischen Erfolg müssen die ausgegebenen Revisionen exakt dieselben Werte
sein, die in derselben Datenbanktransaktion als Revisionen, Einzelmember und
Current-Pointer gespeichert wurden.

Der Operator darf sie nicht nachträglich neu erzeugen, ableiten, normalisieren
oder durch einen zweiten Generatoraufruf ersetzen.

Scheitert die Transaktion, darf keine Resultatdatei entstehen.

## 6. Ergebnisdatei nach Commit

Die bestehende Dateigrenze bleibt maßgeblich:

- Zielpfad existiert noch nicht;
- Zielverzeichnis ist owner-only;
- temporäre Datei wird exklusiv mit Modus 0600 angelegt;
- vollständiges JSON wird synchronisiert und atomar verschoben;
- ein vorhandenes Ziel wird niemals überschrieben.

Scheitert das Schreiben nach Datenbank-Commit, erfolgt keine kompensierende
Mutation und kein Bootstrap-Reopen.

## 7. Exakter Retry nach verlorenem Resultat

Ein erneuter Identity-Bootstrap-Aufruf darf weiterhin ausschließlich den exakt
kanonischen unveränderten Bootstrap-Bestand read-only rekonstruieren.

Bei erfolgreicher Rekonstruktion muss er denselben Vier-Felder-Shape und exakt
dieselben vier IDs wie der verlorene ursprüngliche Erfolg ausgeben.

Insbesondere dürfen Recovery und frischer Erfolg für denselben Bestand nicht
unterschiedliche Revisionen ausgeben.

## 8. Kanonische Revisionsrekonstruktion

Recovery darf die User-Revision nur bestätigen, wenn:

- genau ein Current-Pointer existiert;
- dessen Revision genau einen Member enthält;
- dieser Member exakt der kanonische aktive Bootstrap-Nutzer ist;
- Memberstatus und aktueller Nutzerstatus aktiv sind;
- keine User-Lifecycle-Change-Entscheidung existiert.

Für Workspace gelten dieselben Bedingungen mit dem einen kanonischen aktiven
Bootstrap-Workspace und ohne Workspace-Lifecycle-Change.

Beide Domänen müssen gemeinsam konsistent sein. Teilweise Ausgabe ist
unzulässig.

## 9. Weitere kanonische Bootstrap-Fakten

Die bereits strengeren Recovery-Voraussetzungen bleiben bestehen:

- genau ein aktiver Nutzer;
- genau ein aktiver Workspace;
- genau deren aktive Onboarding-Manager-Bindung;
- aktive User- und Workspace-Lifecycle-Authority für denselben Nutzer;
- keine zusätzlichen Nutzer, Workspaces oder Lifecycle-Bestände.

Die neue Beobachtbarkeit lockert keine dieser Bedingungen.

## 10. Bestehende Installationen

Eine bereits bootstrappte Installation ohne erhaltenes erweitertes Resultat
darf den Identity-Befehl erneut ausführen.

Nur wenn ihr Bestand noch exakt dem kanonischen unveränderten Bootstrap-
Zustand entspricht, liefert Recovery die vier IDs.

Wurde bereits regulär mutiert, ist der Bootstrap kein allgemeiner Current-
Lookup und bleibt neutral `closed`. Jede reguläre Mutation liefert ihre neue
Revision bereits über ihre eigene stabile Change-ID-Retry-Grenze.

## 11. Konkurrenz und Staleness

Bootstrap-Commit und Resultatschreiben sind nicht eine gemeinsame Datenbank-
und Dateisystemtransaktion.

Eine Revision kann deshalb nach ihrem Commit und vor ihrer späteren Nutzung
durch eine andere autorisierte Mutation veralten. Das ist sicher: Der nächste
Lifecycle-Operator prüft sie atomar gegen Current und lehnt stale neutral ab.

Der Bootstrap-Operator behauptet nicht, dass die Revision im Moment des
Dateilesens weiterhin Current ist; er dokumentiert den bestätigten
Bootstrap-Commit.

## 12. Keine allgemeine Current-Abfrage

LQ-228 entscheidet ausdrücklich kein neues Kommando wie:

- `inspect`;
- `status`;
- `list-revisions`;
- `current-user-revision`;
- `current-workspace-revision`.

Eine solche Grenze würde zusätzliche Autorisierungs-, Konsistenz-, Ausgabe-
und Betriebsfragen öffnen, die zur Schließung des initialen Übergangs nicht
notwendig sind.

## 13. Keine revisionslose erste Mutation

User- und Workspace-Lifecycle-Create akzeptieren weiterhin keine
`expected_revision: null`.

Der erste Bestand existiert bereits und kann zwischen Review und Anwendung
verändert werden. Nur exakter Vergleich schützt vor stiller Mutation gegen
eine veraltete Bestandsannahme.

Die zusätzliche Ausgabe schließt die Beobachtungslücke, nicht den
Concurrency-Schutz.

## 14. Neutralität und technische Nichtverfügbarkeit

Nichtkanonischer, zusätzlicher, partieller, inaktiver oder bereits regulär
mutierter Bestand ergibt weiterhin ausschließlich `closed` ohne Detail.

Kann der Vier-Felder-Shape nicht vollständig und konsistent erzeugt oder
rekonstruiert werden, endet der Prozess detailfrei technisch nichtverfügbar.

Dieser Vertrag benennt keinen neuen Exception-Typ. UserId, WorkspaceId,
Revisionen, DSN, SQL, Tabellen-, Constraint- und Treiberdetails dürfen nicht
auf stdout oder stderr erscheinen.

## 15. Kompatibilität und Betriebsübergang

Der Identity-Resultatshape erweitert sich bewusst von zwei auf vier Felder.

Strict-Shape-Consumer und Tests müssen im Implementierungsslice atomar auf den
neuen exakten Shape umgestellt werden. Ein gemischter optionaler Shape ist
nicht zulässig, weil er den operativen Blocker abhängig vom Ausführungspfad
fortbestehen ließe.

Das Runbook muss die beiden Revisionen als nächste `expected_revision`-Werte
für User- beziehungsweise Workspace-Lifecycle erklären, ohne sie in Shell-
History oder Logs zu kopieren.

## 16. Bewusst nicht enthalten

LQ-228 entscheidet keine:

- Migration, Tabelle, Spalte, Seed oder Datenumschreibung;
- neue Lifecycle-Revision oder Änderung ihrer Erzeugung;
- allgemeine Lookup-, Inspect-, List- oder Dump-Grenze;
- Authority-, Nutzer-, Workspace- oder Membership-Mutation;
- Lockerung von Bootstrap-Kanonizität oder Revisionsvergleich;
- HTTP-, UI-, Settings-, Startup- oder Deployment-Verdrahtung;
- Recovery-Ausweitung auf regulär mutierte Bestände;
- konkrete Domainmodell-, Port-, Adapter- oder Signaturänderung.

## 17. Nächster Slice

LQ-229 soll diesen Vertrag in der bestehenden Initial-Bootstrap-
Operatorgrenze implementieren.

Er muss frischen Bootstrap und exakte kanonische Recovery auf denselben
Vier-Felder-Shape bringen, owner-only Dateiverhalten bewahren, bestehende
Runbooks und Tests aktualisieren und PostgreSQL-Retry belegen.

Danach muss der integrierte LQ-227-Nachweis ohne injiziertes Revisionswissen
erneut ausgeführt werden.
