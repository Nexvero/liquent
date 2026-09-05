# LQ-266 — Controlled Release Publication Provider Composition Contract

## 1. Ergebnis

LQ-266 entscheidet den Vertrag für die betriebliche Composition eines
konkreten immutable Publication-Provideradapters.

Der Vertrag verbindet die intern geschlossene LQ-249- bis LQ-265-Kette später
mit genau einem kontrollierten externen Package-Index-Ziel. Dieser Slice
implementiert keinen Netzwerkadapter, Credential-Lookup, Worker, CLI-Befehl
oder Deployment-Wiring.

## 2. Getrennter Publication-Prozess

Providerzugriff gehört in einen dedizierten, kurzlebigen Publication-Worker.

Der HTTP-Prozess, Browser-Session-Auflösung, OIDC-Callback und Research-Runtime
dürfen weder Publication-Credentials noch Creator- oder Inspectoradapter
besitzen.

Ein Webrequest kann keinen Publication-Worker starten oder Providerparameter
einschleusen.

## 3. Explizite Aktivierung

Die Provider-Composition ist standardmäßig vollständig deaktiviert.

Aktivierung verlangt eine vollständige, gemeinsam validierte
Abhängigkeitsgruppe aus:

- Datenbankengine für das maßgebliche System of Record;
- kontrollierter lokaler Artifact-Source;
- aktueller Release-Registry-Projektion;
- genau einer bekannten Providerkonfiguration;
- Credential-Provider;
- read-only Target-Inspector;
- immutable Creator;
- begrenzten Zeit- und Netzwerkregeln.

Teilkonfiguration oder unbekannte Providerart führt fail-closed zu keiner
Composition.

## 4. Ziel stammt aus dem System of Record

Channel-ID, Channel-Revision, Providerart, kanonischer Zielname, Paketname und
Paketversion werden ausschließlich aus Handoff und aktiver Channelrevision
aufgelöst.

Der Worker-Caller darf keine Registry-URL, Repository-ID, Namespace,
Paketversion, Uploadroute oder Fallbackregion liefern.

Die lokale Providerkonfiguration darf nur den intern bekannten kanonischen
Zielnamen auf einen vorab erlaubten technischen Endpoint abbilden.

## 5. Genau eine Providerfamilie pro Adapter

Ein Adapter implementiert genau die Semantik der im Channel persistierten
Providerart `package-index`.

Multi-Provider-Fallback, automatische Spiegelwahl, Region-Failover mit anderer
Identität oder dynamische URL-Auswahl gehören nicht in denselben Adapter.

Weitere Providerfamilien benötigen getrennte Adapter und eine neue explizite
Composition-Entscheidung.

## 6. Credential-Ownership

Publication-Credentials gehören ausschließlich dem dedizierten Worker-
Prozesskonto und dem injizierten Credential-Provider.

Sie werden nicht gespeichert in:

- Publication-, Receipt- oder Recovery-Tabellen;
- Channel- oder Registry-Fakten;
- Handoff, Attempt oder Reassessment;
- CLI-Argumenten oder Requestdateien;
- normalen Environment-Beispielen;
- Logs, Exceptions, Evidence oder Resultdateien.

Der Adapter erhält nur ein kurzlebiges Credential-Handle oder den für genau
einen Aufruf erforderlichen Secretwert.

## 7. Kontrollierte Credential-Quelle

Die spätere betriebliche Composition muss genau eine vorab konfigurierte
Credential-Quelle verwenden, beispielsweise einen Secret-Manager-Handle oder
eine owner-only Datei.

Freie Secretpfade, Environment-Namen, Tokenwerte oder Credentialprofile sind
keine Caller-Eingaben.

Eine dateibasierte Quelle muss regulär, nicht symbolisch verlinkt, nicht leer
und auf das Worker-Prozesskonto beschränkt sein. Ungenügende Zugriffsrechte
führen fail-closed zu technischer Nichtverfügbarkeit.

## 8. Getrennte Read- und Write-Fähigkeit

Der read-only Inspector und der immutable Creator bleiben getrennte Ports.

Der Inspector darf ausschließlich das exakt aufgelöste Ziel lesen. Der Creator
darf ausschließlich die bestätigte fehlende immutable Paketversion anlegen.

Falls der Provider getrennte Read- und Write-Credentials unterstützt, erhält
der Inspector ein read-only Credential und nur der Creator das engere
Write-Credential.

## 9. Gemeinsamer kanonischer Zielkontext

Inspector und Creator müssen denselben validierten Endpoint, dieselbe
Providerinstanz und denselben kanonischen Zielnamen verwenden.

Ein Read gegen Staging und Write gegen Production oder ein Read über Mirror
bei Write zum Origin wäre kein gültiges Read-before-write.

Endpointnormalisierung erfolgt einmal in der Composition und ist für den
einzelnen Publication-Lauf unveränderlich.

## 10. Netzwerkgrenze

Der Adapter erlaubt ausschließlich den vorkonfigurierten HTTPS-Origin.

Verpflichtend sind:

- TLS-Zertifikatsprüfung ohne Disable-Schalter;
- begrenzte Connect- und Gesamtzeit;
- begrenzte Antwortgröße;
- keine Redirects zu anderem Origin;
- keine Proxy- oder CA-Auswahl durch den Caller;
- keine automatische unbegrenzte SDK-Retry-Schleife;
- keine Ausgabe von Authorization-Headern oder Response-Bodies.

DNS-, TLS-, Timeout- und Protokollfehler bleiben technische
Nichtverfügbarkeit.

## 11. Exakte Zielinspektion

Der Inspector fragt ausschließlich Paketname und exakte Paketversion des
kontrollierten `ReleasePublicationTarget` ab.

Ein eindeutig bestätigtes Nichtvorhandensein wird als `None` dargestellt.

Authentication-/Authorization-Fehler, Rate-Limits, Serverfehler, ungültige
Antworten, unvollständige Metadaten und Netzwerkfehler sind niemals
bestätigte Abwesenheit.

## 12. Kanonische Observation

Eine sichtbare Providerantwort wird nur akzeptiert, wenn sie eindeutig bindet:

- kanonische externe Artefaktidentität;
- unveränderliche Providerrevision oder äquivalente ETag-Identität;
- Paketname und exakte Version;
- Wheel-SHA-256;
- bestätigte Sichtbarkeit.

Fehlt eines dieser Felder, bleibt der Zustand technisch unbekannt. HTML-
Fehlerseiten, frei formatierte Meldungen oder Dateinamen allein sind keine
Observation.

## 13. Immutable Create-only

Der Creator verwendet ausschließlich eine Create-only-Operation.

Unzulässig sind:

- Overwrite oder Replace;
- Upsert;
- mutable Tags oder `latest`;
- Delete-then-create;
- Yank, Unyank oder Deprecation;
- automatische Versionserhöhung;
- Upload unter einem alternativen Namen.

Unterstützt der Provider keine belastbare immutable Create-Semantik, darf er
nicht für diese Composition verwendet werden.

## 14. Payload-Grenze

Der Creator erhält ausschließlich die durch LQ-255 erneut verifizierten
Artefaktbytes und den kontrollierten Zielkontext.

Er darf Paketname, Version, Wheel, Checksums, Signatur oder Promotion-Evidence
nicht neu erzeugen, transformieren oder aus einem anderen Pfad nachladen.

Temporäre Provider-SDK-Dateien müssen in einem exklusiven Worker-
Temporärverzeichnis liegen und nach dem Aufruf entfernt werden. Sie sind keine
persistente Artifact-Source.

## 15. Idempotenzidentität

Der Adapter übernimmt exakt die vom jeweiligen Create-Port gelieferte stabile
Idempotenzidentität:

- Attempt 1: Execution-ID;
- Attempt 2: Attempt-2-ID.

Er ersetzt sie nicht durch Zufallswerte, Zeitstempel oder SDK-generierte
Request-IDs.

Native Provider-Idempotenz wird verwendet, sofern sie für die konkrete
Create-Operation belastbar unterstützt wird.

## 16. Keine semantische SDK-Retry-Schleife

Nach Übergabe eines Create-Requests darf der Adapter nicht selbstständig einen
zweiten semantischen Upload beginnen.

Transportbibliotheken dürfen nur sicher nachweislich vor Übertragung
gescheiterte Verbindungen intern wiederaufnehmen. Sobald ein externer Effekt
möglich ist, kehrt der Adapter zurück oder meldet technische
Nichtverfügbarkeit; die persistente Kette übernimmt Unknown-Outcome und
Reconciliation.

## 17. Provider-Acknowledgement

Eine positive Create-Antwort wird ausschließlich in eine repr-freie
`ReleasePublicationCreateAcknowledgement` mit nicht leerer Provider-Request-ID
übersetzt.

Raw Response, Token, Upload-URL, Header oder Response-Body werden weder
persistiert noch zurückgegeben.

Die Acknowledgement ist ausdrücklich kein Receipt und kein
Sichtbarkeitsnachweis.

## 18. Konflikt- und Already-exists-Antworten

HTTP- oder SDK-`already exists` ist kein automatischer Erfolg.

Der Creator meldet keinen Receipt und überschreibt nicht. Die persistente
Execution bleibt nach möglichem Write `outcome_unknown`; ausschließlich der
read-only Inspector kann anschließend Bytegleichheit oder Konflikt
feststellen.

## 19. Fehlerabbildung

Der Adapter darf nach außen nur typisierte gültige Observation,
Acknowledgement, bestätigte Abwesenheit oder technische Nichtverfügbarkeit
liefern.

Providertexte, URLs, Accountnamen, Requestheader, Tokens, interne Tenant-IDs
und rohe Statusdetails verlassen die Adaptergrenze nicht.

Die Persistenzschicht entscheidet weiterhin neutral versus technisch
nichtverfügbar und bewahrt jeden möglichen Write als `outcome_unknown`.

## 20. Logging und Telemetrie

Zulässige Telemetrie ist auf nicht-sensitive Betriebsfakten begrenzt:

- Adaptertyp;
- grobe Operationsart `inspect` oder `create`;
- Ergebnisfamilie;
- Dauer und begrenzte Fehlerkategorie;
- intern korrelierbare, nicht geheime Execution- oder Attemptreferenz.

Artefaktbytes, Hashlisten, Credentials, Providerantworten und vollständige
Ziel-URLs werden nicht geloggt.

## 21. Prozess- und Dateirechte

Der spätere Worker läuft unter einem dedizierten, nicht interaktiven
Prozesskonto mit minimalen Dateirechten.

Er benötigt keinen Zugriff auf Browser-Session-Secrets, OIDC-Client-Secrets,
Research-Daten, Signing-Private-Keys, Deployment-Credentials oder
Authority-Operator-Requestdateien.

Publication- und Signing-Prozesskonto müssen getrennt bleiben.

## 22. Revocation und Laufzeit

Credentials können technisch für einen bereits gestarteten Netzwerkaufruf
nicht durch einen Datenbankcommit zurückgerufen werden.

Deshalb bleibt der persistente Write-Start kurz, und jeder Abschluss liest
aktuelle Channel-, Publisher- und Release-Authority erneut. Revocation nach
möglichem Effekt bewahrt externe Realität mit `pending` Reassessment.

Die Adapter-Composition darf keinen positiven Authority-Cache hinzufügen.

## 23. Start- und Shutdown-Verhalten

Worker-Startup führt keinen Providerzugriff, Preflight oder Upload aus.

Er validiert nur die vollständige lokale Composition. Publication beginnt
erst mit einer expliziten bestehenden Execution- und Attemptreferenz.

Shutdown verwirft kurzlebige Credentials und schließt Clients. Er darf keinen
halbfertigen Attempt als Erfolg markieren; persistiertes `write_started`
bleibt über die bestehende Crash-Wiederaufnahme fail-closed.

## 24. Keine neue Authority

Besitz des Worker-Prozesskontos, Credential-Zugriff oder Startberechtigung ist
keine Publisher-Authority.

Vor jedem Write lösen die bestehenden Persistenzadapter aktuelle
Publisher-, Channel-, Registry-, Signer- und Key-Fakten aus dem System of
Record auf.

Es gibt keinen Environment-Allow, Operator-Role-Bypass oder Emergency-Upload.

## 25. Retention

Provider-Credentials und rohe Antworten werden nicht als Auditfakten
aufbewahrt.

Attempts, Recoveries, Receipts, externe kanonische Identitäten,
Providerrevisionen und Reassessments folgen weiterhin den bestehenden
historienerhaltenden Retention- und Nichtwiederverwendungsregeln.

## 26. Bewusst nicht entschieden

LQ-266 entscheidet keine:

- konkrete Providerbibliothek oder Hersteller-API;
- Python-Klasse, neues Modell, neuen Port oder neue Exception;
- Credential-Dateiformat oder Secret-Manager-Produkt;
- Tabelle, SQL, Migration oder Seed;
- Worker-CLI, Scheduler, Queue oder Service-Unit;
- Runtime-, Compose-, CI-, Git- oder Deploymentverdrahtung;
- Withdrawal-, Yank- oder Delete-Funktion.

Es erfolgt kein Dateisystem-, Provider-, Git- oder Deploymentwrite.

## 27. Nachweis und Folgeordnung

LQ-265 belegt bereits die vollständige providerneutrale Zwei-Attempt-
Zustandsmaschine auf SQLite und PostgreSQL 16.

LQ-266 friert die betriebliche Adapter- und Composition-Grenze ein. Head bleibt
`20260819_0024` mit 24 linearen Migrationen; die vollständige Pflichtsuite
bleibt bei:

```text
3234 passed, 530 warnings
```

Der nächste Slice LQ-267 implementiert zuerst einen providerneutral testbaren
Package-Index-Inspector und immutable Creator samt kontrollierter
Credential-/Endpoint-Konfiguration. Worker-CLI und Production-Wiring bleiben
danach getrennte Slices.
