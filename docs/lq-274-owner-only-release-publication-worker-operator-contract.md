# LQ-274 — Owner-only Release Publication Worker Operator Contract

## 1. Ergebnis

LQ-274 friert den Prozessvertrag für den owner-only Offline-Operator ein, der
später genau eine LQ-273-Worker-Composition aufbaut und genau eine geschlossene
Publication-Arbeitseinheit ausführt.

Der Vertrag entscheidet private Eingabequellen, Trennung von Work-Request und
lokaler Providerkonfiguration, interne ID-Erzeugung, detailfreie Ausgaben und
Exitcodes.

Dieser Slice implementiert noch keinen CLI-Befehl oder Console Entry Point.

## 2. Prozessgrenze

Der spätere Operator ist ein explizit gestarteter, kurzlebiger Offline-Prozess.

Er ist keine:

- HTTP-Route oder Browserfunktion;
- OIDC-, Session- oder Research-Komponente;
- App-Startup- oder Lifespan-Funktion;
- Queue, Scheduler, Watcher oder Daemon;
- automatische CI-, Release- oder Deploymentaktion.

Jeder Aufruf bearbeitet genau eine persistente Publication-Execution und endet
anschließend.

## 3. Dediziertes Prozesskonto

Der Operator läuft unter einem nicht interaktiven Publication-Prozesskonto.

Dieses Konto besitzt ausschließlich die minimal erforderlichen Leserechte für
Operator-Konfiguration, Artifact-Dateien und Credential sowie den notwendigen
Datenbankzugriff.

Es besitzt keinen Zugriff auf:

- Signing-Private-Keys;
- OIDC-Client- oder Browser-Session-Secrets;
- Research-Datenbestände;
- Deployment- oder Infrastruktur-Credentials;
- Authority-Operator-Requestdateien anderer Grenzen.

Besitz des Prozesskontos gewährt keine Publisher-Authority.

## 4. CLI nimmt nur Dateipfade an

Der spätere Command akzeptiert ausschließlich Pfade zu vorab bereitgestellten
lokalen Dateien:

- Datenbank-URL-Datei;
- Work-Request-Datei;
- Artifact-Source-Datei;
- Providerkonfigurationsdatei;
- Executor-ID-Datei;
- Promotion-Verifier-ID-Datei.

IDs, URLs, Credentials, Timeouts, Hashes und fachliche Entscheidungen sind
keine direkten Kommandozeilenwerte.

Es gibt keine Environment-Variable als Fallback für eine dieser Quellen.

## 5. Gemeinsame private Dateigrenze

Alle sechs Eingabedateien und die von der Providerkonfiguration referenzierte
Credential-Datei müssen:

- existieren;
- reguläre Dateien sein;
- dürfen keine symbolischen Links sein;
- dem effektiven Prozessnutzer gehören;
- genau einen Hardlink besitzen;
- ausschließlich Modus `0400` oder `0600` besitzen;
- begrenzte Größe und gültiges UTF-8 einhalten, soweit Text erwartet wird.

Die spätere Implementierung öffnet sicher mit `O_NOFOLLOW` und `O_CLOEXEC` und
prüft das geöffnete Objekt über `fstat`.

Unsichere Rechte, Eigentümer, Links oder Dateitypen sind technische
Nichtverfügbarkeit, keine fachliche Ablehnung.

## 6. Datenbank-URL-Datei

Die Datenbank-URL wird aus einer getrennten privaten Datei gelesen.

Sie erscheint nicht in Prozessargumentliste, Work-Request, Providerkonfiguration,
stdout oder stderr.

Die URL muss eine explizite unterstützte Datenbank adressieren. Es gibt keinen
automatischen SQLite-, In-Memory- oder Default-DSN-Fallback.

Der Operator migriert das Schema nicht. Fehlender oder falscher Migration-Head
endet detailfrei technisch nicht verfügbar.

## 7. Geschlossener Work-Request

Die Work-Request-Datei ist kanonisches JSON mit exakt fünf Feldern:

- `execution_id`;
- `handoff_id`;
- `publisher_authority_id`;
- `channel_id`;
- `expected_channel_revision`.

Jeder Wert ist ein nicht leerer stabiler interner String und wird unverändert
in den bestehenden Domain-Typ überführt.

Unbekannte, fehlende, doppelte oder falsch typisierte Felder werden vollständig
abgelehnt.

## 8. Keine offene Work-Steuerung

Der Work-Request enthält insbesondere keine:

- Attempt-ID oder Attempt-Nummer;
- Phase, Status oder Retry-Entscheidung;
- Rolle, Capability oder Allow-Boolean;
- Providerart, Origin, Zielname oder Paketversion;
- Credential, Secretpfad oder Authentication-Header;
- Artefaktpfad, Artefaktbytes oder Hash;
- Observation, Acknowledgement, Receipt oder Reconciliation-Art;
- Outputpfad, Deploymentziel oder Git-Referenz.

Der persistente LQ-272-State-Lookup entscheidet allein, welcher Schritt aktuell
zulässig ist.

## 9. Separate Artifact-Source-Datei

Die lokale Artifact-Source-Datei ist von Work-Request und Providerkonfiguration
getrennt.

Sie enthält exakt:

- dieselbe stabile Handoff-ID;
- absoluten Bundle-Pfad;
- absoluten detached-SSHSIG-Pfad;
- absoluten Promotion-Evidence-Pfad.

Sie enthält keine Hashwerte, Paketversion, Registryrevision, Signer-, Key- oder
Authority-Behauptung.

Unbekannte Felder oder relative Pfade werden abgelehnt.

## 10. Artifact-Bindung aus dem System of Record

Die Handoff-ID der Artifact-Source-Datei muss exakt dem geschlossenen Request
entsprechen.

Bundle-, Signatur- und Evidence-Hashes werden nicht aus der Datei übernommen.
Die spätere Composition löst sie aus dem persistenten Handoff auf und bindet
erst danach die drei lokalen Pfade an den vollständigen
`ReleasePublicationArtifactBinding`.

Die bestehende LQ-255-Integritätsprüfung liest und hasht alle Bytes erneut.

Ein Dateipfad ist deshalb weder Hashbehauptung noch Publication-Authority.

## 11. Artifact-Dateiregeln

Bundle, Signatur und Promotion-Evidence müssen reguläre, nicht verlinkte und
read-only zugängliche Dateien sein.

Der Signaturdateiname muss exakt `<bundle-name>.sshsig` sein.

Die Dateien werden nicht geschrieben, verschoben, ersetzt oder gelöscht.

Ihre Bytes dürfen nach Aufbau nicht durch einen alternativen Pfad, eine URL
oder Providerantwort substituiert werden.

Datei- und Byteintegrität bleiben vollständig durch die bestehende persistente
Hash- und Signaturprüfung bestimmt.

## 12. Separate Providerkonfiguration

Die Providerkonfigurationsdatei ist kanonisches JSON mit exakt:

- kanonischem HTTPS-Origin;
- lokalem Zielnamen;
- absolutem Credential-Dateipfad;
- positiven Connect-, Read- und Gesamtzeitgrenzen;
- positiver maximaler Requestgröße;
- positiver maximaler Responsegröße.

Unbekannte Providerfamilien, zusätzliche Origins, Mirrors oder Fallbackziele
sind nicht zulässig.

Der Work-Request kann diese Werte nicht überschreiben.

## 13. Provider- und Zielbindung

Die Operatorgrenze unterstützt zunächst ausschließlich `package-index`.

Persistierter Providerkind und Zielname müssen über die LQ-267-/LQ-273-Kette
exakt zur lokalen Providerkonfiguration passen.

Ein Request für einen anderen Channel, Zielnamen oder Provider führt zu keinem
Netzwerkzugriff.

Die lokale Konfiguration ist technische Erreichbarkeitskonfiguration und keine
fachliche Publication-Freigabe.

## 14. Credential-Datei

Die Credential-Datei folgt unverändert der LQ-269-Grenze:

- owner-only `0400` oder `0600`;
- regulär, einfach verlinkt und `O_NOFOLLOW` geöffnet;
- höchstens 4096 Credential-Bytes plus optional genau ein abschließendes LF;
- gültiges UTF-8 ohne Whitespace oder Steuerzeichen.

Das Credential wird genau einmal pro Operatorlauf geladen und nur im besessenen
Package-Index-Client gehalten.

Es erscheint nicht in Request, Datenbank, Resultat, Logs oder Fehlerausgaben.

## 15. Getrennte Executor-ID

Die Publication-Executor-ID wird aus einer eigenen privaten Datei gelesen.

Sie identifiziert ausschließlich den technischen Executor-Fakt des Attempt-
Preflights und erteilt keine Publisher-Authority.

Die Datei enthält exakt eine nicht leere ID mit optional genau einem finalen
LF und keine Rolle, Capability oder Revision.

Der Work-Request kann die Executor-ID nicht wählen.

## 16. Getrennte Promotion-Verifier-ID

Die Promotion-Verifier-ID stammt aus einer weiteren privaten Datei.

Sie bindet die aktuelle Registry-Projektion und die erneute Promotion-Evidence-
Verifikation.

Sie ist getrennt von Publication-Executor, Publisher-Authority und Signing-
Executor.

Auch diese Identität ist kein Allow-Fakt und nicht im Work-Request enthalten.

## 17. Interne ID-Erzeugung

Attempt-, Receipt-, Recovery- und Reassessment-IDs werden ausschließlich im
Operatorprozess kryptografisch sicher erzeugt.

Sie werden nicht aus CLI, Environment, Requestdatei oder Providerantwort
übernommen.

Jede erzeugte ID ist nicht leer, opak und domänenspezifisch typisiert.

Generatoren werden erst von den bestehenden persistenten Adaptern aufgerufen,
wenn eine neue ID tatsächlich benötigt wird.

## 18. Retry-Stabilität der IDs

Der Operator speichert neu erzeugte IDs nicht in einer separaten Datei.

Die jeweilige atomare Datenbankentscheidung ist ihr einziger stabiler
Retry-Anker.

Ein Retry derselben Work-Request-Datei liest bestehende Attempt-, Receipt- oder
Recovery-Fakten und erzeugt keine Ersatz-ID.

Ein Absturz vor einem Commit darf beim nächsten Lauf eine neue unpersistierte
ID erzeugen; eine bereits persistierte ID wird niemals ersetzt oder für einen
anderen Fakt wiederverwendet.

## 19. Genau eine Engine und ein Client

Jeder Operatorlauf baut genau eine Engine aus der privaten URL-Datei und genau
eine LQ-269-Package-Index-Composition aus der privaten Providerkonfiguration.

Beide werden an genau eine LQ-273-Worker-Composition übertragen.

Es gibt keinen zweiten Client für Reconciliation, keinen separaten Write-
Origin und keine Wiederverwendung im Webprozess.

## 20. Genau ein Work-Aufruf

Nach erfolgreichem Aufbau ruft der Operator exakt einmal:

```text
composition.worker.process(request)
```

auf.

Er führt keine Schleife, kein Polling und keinen automatischen Retry aus.

Ein weiterer Zustandsübergang benötigt einen neuen expliziten Prozessaufruf
mit derselben bewahrten Work-Request-Datei.

## 21. stdout-Ergebnisse

stdout enthält bei einem normalen Work-Ergebnis genau eine Zeile kanonisches
kompaktes JSON mit exakt einem Feld `outcome`.

Zulässige Werte und Exitcodes sind:

- `published`, Exit `0`;
- `published_reassessment_required`, Exit `6`;
- `not_published`, Exit `7`;
- `publication_conflict`, Exit `8`;
- `pending_reconciliation`, Exit `9`;
- `not_actionable`, Exit `5`.

Kein Ergebnis enthält IDs, Providerdetails, Hashes, Pfade oder Authority-
Bestände.

## 22. Bedeutung der normalen Outcomes

`published` bedeutet ausschließlich, dass ein persistentes bestätigtes Receipt
vorliegt.

`published_reassessment_required` bewahrt denselben externen Fakt, verlangt
aber getrennte Security-Folgearbeit und ist deshalb kein Exit 0.

`not_published` und `publication_conflict` sind terminale persistente
Ergebnisse, aber kein Operatorerfolg.

`pending_reconciliation` verlangt einen späteren expliziten read-only
Wiederaufnahmeaufruf und startet keinen automatischen Create.

`not_actionable` vereinheitlicht neutrale Abwesenheit, stale Referenz,
Authority-Entzug und aktuell nicht zulässigen Übergang ohne Detailoffenlegung.

## 23. Fehler und stderr

Ungültige oder unsichere Eingabedateien enden mit Exit `2` und stderr:

```json
{"error":"release_publication_operator_input_rejected"}
```

Technische Nichtverfügbarkeit endet mit Exit `4` und stderr:

```json
{"error":"release_publication_operator_unavailable"}
```

stdout bleibt in beiden Fehlerfällen leer.

Parser-, Domain-, Datei-, Datenbank-, Artifact-, Credential-, TLS-, Provider-,
Clock-, Generator- und Close-Details werden nicht reflektiert.

## 24. Exception-Grenze

Die spätere Prozessgrenze fängt reguläre `Exception`-Fehler und vereinheitlicht
sie detailfrei.

`BaseException`, insbesondere KeyboardInterrupt und SystemExit außerhalb der
expliziten Exitsteuerung, wird nicht als technischer Operatorfehler verschluckt.

Ein Fehler nach möglichem Provider-Write bleibt persistent
`outcome_unknown`; die Ausgabe behauptet weder Erfolg noch Abwesenheit.

## 25. Ressourcenabschluss

Engine und Providerclient werden in einem `finally`- beziehungsweise Context-
Manager-Pfad bei jedem normalen Ergebnis, fachlicher Ablehnung und technischen
Fehler geschlossen.

Der Close-Pfad löst keinen Provider-Read, Create oder Datenbankübergang aus.

Ein Close-Fehler kann ein zuvor erzeugtes stdout-Ergebnis verhindern und endet
detailfrei technisch nicht verfügbar. Er darf einen persistierten Abschluss
nicht zurückrollen oder umdeuten.

## 26. Logging

Der Operator erzeugt standardmäßig keine zusätzliche fachliche Logdatei.

Zulässige externe Prozessmetrik ist auf Commandname, Dauer, Exitcode und grobe
Outcome-Familie begrenzt.

Unzulässig in Logs, stdout und stderr sind:

- DSN und Datenbankhost;
- alle lokalen Pfade;
- Credential und Authorization-Header;
- Execution-, Handoff-, Attempt- und Authority-IDs;
- Paketversion und Hashlisten;
- Providerantworten und Request-IDs;
- ursprüngliche Exceptions oder SQL.

## 27. Request-Retention

Die Work-Request-Datei ist der bewahrte Operator-Retry-Anker und darf während
eines unklaren oder nicht terminalen Zustands nicht verändert werden.

Artifact-Source- und Providerkonfiguration werden ebenfalls nicht vom Operator
mutiert.

Ihre betriebliche Retention muss mindestens alle erforderlichen Wiederaufnahme-
und Auditzeiträume abdecken.

Persistente Execution-, Attempt-, Recovery-, Receipt- und Reassessment-Fakten
bleiben die normative Historie; lokale Dateien ersetzen sie nicht.

## 28. Keine automatische Reparatur

Der Operator repariert keine:

- zu weiten Dateirechte;
- fehlenden oder partiellen Artifact-Dateien;
- stale Requestreferenzen;
- falschen Migration-Head;
- widerrufene Authority;
- Providerkonflikte oder Unknown-Outcomes.

Er überschreibt, löscht oder normalisiert keine Eingabedatei.

Jede Korrektur verlangt eine getrennte kontrollierte Betriebs- oder
Securityentscheidung.

## 29. Bewusst nicht entschieden

LQ-274 entscheidet keine:

- Python-Modul-, Funktions- oder Klassensignatur;
- konkrete Console-Entry-Point-Bezeichnung;
- JSON-Schema-Datei oder Konfigurationsgenerator;
- Runbook-, Service-Unit-, Container- oder Schedulerintegration;
- Secret-Manager-, KMS- oder Cloud-Provider-Anbindung;
- Migration, Tabelle, SQL oder Seed;
- Withdrawal-, Yank-, Delete- oder Rollbackfunktion;
- Git-, Package-Repository- oder Deploymentautomation.

Es erfolgt kein Datei-, Provider-, Git- oder Deploymentwrite.

## 30. Nachweis und Folgeordnung

LQ-273 belegt bereits die vollständige lokale Composition und ihren
Ressourcenabschluss. Die Pflichtsuite bleibt bei:

```text
3330 passed, 581 warnings
```

Der Migration-Head bleibt `20260819_0024` mit 24 linearen Migrationen.

LQ-275 implementiert als nächsten Slice den owner-only Offline-Operator samt
geschlossenem Parser, sicheren Dateiquellen, interner ID-Erzeugung und
detailfreier Prozessausgabe, weiterhin ohne Scheduler oder automatische
Production-Aktivierung.
