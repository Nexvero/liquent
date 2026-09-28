# LQ-278 — Owner-only Release Registry Bootstrap and Key Activation Operator Contract

## Ergebnis

LQ-278 friert die Prozessverträge für die ersten beiden fehlenden Grenzen aus
dem LQ-277-Readiness-Audit ein:

- einmaliger Release-Registry-Bootstrap;
- Proof- und Approval-gebundene Aktivierung des ersten Signing-Keys.

Die Grenzen bleiben getrennte kurzlebige owner-only Offline-Prozesse.

Dieser Slice implementiert noch keinen Command, Entry Point, Kryptografie-
Adapter, Runbook oder Production-Wiring.

## Prozess- und Authority-Trennung

Registry-Bootstrap erzeugt die erste Registry, aber keinen aktiven Key.

Key-Aktivierung ist eine spätere Lifecycle-Mutation mit aktuellem Actor,
Proof of Possession und unabhängiger Approval-Identität.

Bootstrap-Besitz, Datenbankzugriff, privater Key, Signing-Executor,
Promotion-Verifier oder Publication-Publisher gewähren keine
Registry-Lifecycle-Authority.

## Zwei getrennte Commands

Die spätere Implementierung stellt zwei Entry Points bereit:

- `liquent-release-registry-bootstrap`;
- `liquent-release-key-activation`.

Sie werden nicht als Unterkommandos des Signing-, Promotion- oder Publication-
Operators ausgeführt und nicht beim App-Startup aufgerufen.

## Dedizierte Prozesskonten

Der Bootstrap läuft unter einem nicht interaktiven Registry-Bootstrap-Konto.

Die Aktivierung läuft unter einem getrennten Lifecycle-Operator-Konto. Die
Proof-Erzeugung mit dem privaten Key und die unabhängige Approval-Erzeugung
liegen außerhalb beider Datenbankprozesse.

Kein Prozesskonto benötigt Research-, OIDC-, Session-, Deployment- oder
Provider-Credentials.

## Gemeinsame private Dateigrenze

Alle CLI-Argumente sind ausschließlich absolute Pfade zu vorab erzeugten
lokalen Dateien.

Jede Eingabedatei muss regulär, nicht symbolisch verlinkt, dem effektiven
Prozessnutzer zugeordnet, genau einfach verlinkt und exakt Modus `0400` oder
`0600` sein.

Die Implementierung öffnet descriptor-basiert mit `O_NOFOLLOW` und
`O_CLOEXEC`, prüft das geöffnete Objekt über `fstat` und liest begrenzt.

Unsichere Eigentümer-, Link-, Modus- oder Dateitypfakten enden detailfrei
technisch nicht verfügbar. Ungültiger Inhalt wird als Input abgelehnt.

## Datenbank und Readiness

Jeder Command erhält die Datenbank-URL ausschließlich über eine private Datei.

Es gibt keinen Environment-, SQLite-, In-Memory- oder Default-DSN-Fallback.
Der exakte Migration-Head muss vor jeder weiteren Verarbeitung ready sein.

Die Operatoren migrieren nicht und reparieren keinen partiellen Bestand.

## Bootstrap-Request

Der Bootstrap-Request ist kanonisches kompaktes JSON mit sortierten Schlüsseln,
finalem LF und exakt einem Feld:

```json
{"bootstrap_id":"STABLE_BOOTSTRAP_ID"}
```

Die ID wird vor dem ersten Aufruf kryptografisch sicher erzeugt und als
stabiler Retry-Anker bewahrt.

Authority-, Key-, Registry- und Policy-IDs sind keine Requestfelder.

## Öffentliche Schlüsselquelle

Der Bootstrap erhält den ersten öffentlichen Schlüssel aus einer getrennten
privaten Datei.

Sie enthält exakt eine kanonische `ssh-ed25519`-Public-Key-Zeile mit optional
genau einem finalen LF und ohne Kommentar.

Der Operator berechnet den kanonischen SHA-256-Fingerprint unabhängig aus
diesem Schlüssel. Ein caller-gelieferter Fingerprint wird nicht akzeptiert.

Private Keybytes erreichen Bootstrap, Datenbank und Resultat niemals.

## Bootstrap-Aufruf

Der spätere Bootstrap-Command akzeptiert ausschließlich:

```text
--database-url-file PATH
--request PATH
--public-key-file PATH
```

Er baut genau eine Engine, prüft Readiness, validiert den Public Key und ruft
den bestehenden LQ-241-Adapter genau einmal auf.

Es gibt keine Schleife, Adoption oder automatische Key-Aktivierung.

## Interne Bootstrap-ID-Erzeugung

Lifecycle-Authority-, Signer-Authority-, Key-, Registry-Revision- und Policy-
Revision-ID werden ausschließlich intern kryptografisch sicher erzeugt.

Jeder Generator wird erst nach atomar bestätigter vollständiger Registry-Leere
gezogen. Persistierte IDs werden bei exaktem Retry nicht ersetzt.

Keine ID wird aus Public Key, Fingerprint, Zeit, Host oder Bootstrap-ID
abgeleitet.

## Bootstrap-Erfolgsausgabe

Ein neuer oder exakt rekonstruierter erfolgreicher Bootstrap liefert auf
stdout genau eine kanonische JSON-Zeile mit:

- `bootstrap_id`;
- `lifecycle_authority_id`;
- `signer_authority_id`;
- `key_id`;
- `registry_revision_id`;
- `policy_revision_id`.

Der Outcome heißt in beiden Fällen `bootstrapped`; neu und Retry werden nicht
als unterschiedliche fachliche Entscheidungen behauptet.

Die geschützte Ausgabe ist der kontrollierte Übergabefakt für Challenge und
spätere Lifecycle-Arbeit. Sie enthält keinen Key oder Fingerprint.

## Bootstrap-Ablehnung und Konflikt

Eine andere Bootstrap-ID nach irgendeiner Registry-Historie endet neutral
`not_bootstrapped` mit Exit `5` und ohne Bestandsdetails.

Dieselbe Bootstrap-ID mit anderem Public Key endet als detailfreier Konflikt
mit Exit `3`.

Ungültiger Input endet mit Exit `2`, technische Nichtverfügbarkeit mit Exit
`4`. Fehlerausgaben enthalten ausschließlich stabile Fehlercodes.

## Keine Bootstrap-Wiederöffnung

Verlust, Revocation, Deaktivierung oder beschädigte lokale Ausgabe öffnen den
Bootstrap nie wieder.

Bei verlorenem Erfolgsergebnis wird exakt dieselbe Bootstrap-ID mit exakt
demselben Public Key wiederholt.

Eine neue ID oder ein Ersatzkey ist kein Recoveryweg.

## Aktivierung als Zwei-Phasen-Prozess

Der Aktivierungsoperator besitzt die expliziten Modi:

- `challenge` materialisiert eine aktuelle kanonische Challenge;
- `apply` wendet Proof und unabhängiges Approval auf dieselbe Bindung an.

`challenge` mutiert die Registry nicht. `apply` rekonstruiert die Challenge
aus dem aktuellen System of Record und vertraut keinem caller-gelieferten
Challengeinhalt als Authority.

## Geschlossener Aktivierungsrequest

Beide Modi verwenden dieselbe unveränderte kanonische Requestdatei mit exakt:

```json
{"actor_authority_id":"LIFECYCLE_AUTHORITY_ID","change_id":"STABLE_CHANGE_ID","expected_revision":"CURRENT_REGISTRY_REVISION_ID","key_id":"INACTIVE_KEY_ID"}
```

Sie enthält keine resultierende Revision, Reviewer-ID, Public-Key-Datei,
Fingerprint-, Status-, Rolle-, Capability- oder Allow-Behauptung.

Change-ID und Request werden bis zum eindeutigen Abschluss unverändert bewahrt.

## Challenge-Materialisierung

Der `challenge`-Modus akzeptiert zusätzlich genau einen abwesenden absoluten
Ausgabepfad.

Er löst aktuelle Revision, aktiven Lifecycle-Actor, inaktiven Key, aktive
Signer-Authority, Public Key und Fingerprint aus der Registry auf.

Bei positiver Auflösung materialisiert er exklusiv die bereits in LQ-242
definierten kanonischen Challengebytes mit Namespace
`liquent-release-key-possession-v1`.

Vorhandene Ziele werden nicht geöffnet, ersetzt oder gelöscht. Ausgabe erfolgt
owner-only über temporäre exklusive Datei, vollständigen Write, `fsync`,
exklusiven finalen Link und Directory-Sync.

## Challenge ist kein Ticket

Eine materialisierte Challenge gewährt keine Aktivierung und reserviert keine
Revision.

Zwischen `challenge` und `apply` können Revocation, Revisionwechsel oder
Actor-Deaktivierung eintreten. `apply` prüft alle aktuellen Fakten erneut und
endet dann neutral.

Die Challenge darf nicht editiert, normalisiert oder für eine andere Change-,
Actor-, Key- oder Revisionbindung wiederverwendet werden.

## Proof of Possession

Der Proof wird außerhalb des Datenbankoperators mit genau dem privaten Key
über die exakten Challengebytes erzeugt.

Der spätere Proof-Verifier ist eine fest komponierte kontrollierte
Kryptografiegrenze. Proofbytes, Algorithmus und Format werden nicht durch ein
Requestfeld ausgewählt.

Der Proof ist keine Release-Signatur, keine Signing-Decision und keine
Promotion-Evidence.

## Unabhängiges Approval

Approval wird von einer Person oder Security-Grenze erzeugt, deren stabile
Reviewer-ID von der kontrollierten Approval-Verifier-Composition stammt.

Reviewer-Vertrauen, Reviewer-ID und Reviewer-Key dürfen weder aus dem Request
noch aus einer frei wählbaren CLI-Trustdatei übernommen werden.

Der Verifier muss dieselben Challengebytes binden und darf den Lifecycle-Actor
nicht als Reviewer zurückgeben. Fehlende Unabhängigkeit endet neutral.

Die konkrete Proof- und Approval-Kryptografie sowie deren feste Trust-
Composition werden vor Implementierung in einem eigenen Slice entschieden.

## Apply-Aufruf

Der spätere Apply-Modus akzeptiert ausschließlich Pfade:

```text
--database-url-file PATH
--request PATH
--proof PATH
--approval PATH
```

Er akzeptiert keinen Challengepfad als normative Eingabe. Der operatorintern
rekonstruierte Challengeinhalt ist allein maßgeblich.

Proof und Approval werden begrenzt als opaque Bytes gelesen und unverändert an
die fest komponierten Verifier übergeben.

## Aktivierungsergebnis

Neue oder exakt wiederholte Aktivierung liefert kanonisches JSON mit:

- `outcome` gleich `activated`;
- `change_id`;
- `key_id`;
- `registry_revision_id` der resultierenden Revision;
- `reviewer_id`.

Diese geschützte Ausgabe enthält keine Challenge-, Proof-, Approval-, Public-
Key- oder Fingerprintbytes.

## Aktivierungs-Ablehnung und Konflikt

Stale Revision, inaktiver Actor, falscher Keystatus, fehlender Proof,
unwirksames Approval oder gleiche Actor-/Reviewer-Identität enden neutral
`not_activated` mit Exit `5`.

Dieselbe Change-ID mit abweichendem Actor, Key, erwarteter Revision, Proof oder
Approval endet detailfrei Konflikt mit Exit `3`.

Inputfehler verwenden Exit `2`, technische Verifier-, Datenbank-, Generator-
oder Dateifehler Exit `4`.

## Exakter Aktivierungsretry

Nach unklarem Ausgang wird exakt derselbe Request mit bytegleichem Proof und
Approval erneut ausgeführt.

Ein persistierter Retry liefert dieselbe resultierende Revision und Reviewer-
ID ohne erneute Verifikation oder Generatorzüge.

Neue Change-ID, neue Proofbytes oder neues Approval sind kein Retry und dürfen
nicht automatisch erzeugt werden.

## Ausgabe- und Logginggrenze

stdout enthält ausschließlich die jeweilige kanonische Erfolgs- oder neutrale
Outcome-Zeile. stderr enthält bei Fehlern nur einen stabilen Code.

DSN, Pfade, Public Key, Fingerprint, Challenge, Proof, Approval, gespeicherter
Bestand, SQL und ursprüngliche Exceptions werden nicht geloggt oder reflektiert.

Externe Prozessmetriken bleiben auf Command, Modus, Dauer, Exitcode und grobe
Outcome-Familie begrenzt.

## Ressourcenabschluss

Jeder Aufruf baut genau eine Engine und schließt sie in allen Pfaden.

Kryptografie- und Approval-Verifier sind explizit komponierte Ressourcen mit
festem Ownership. Aufbau führt keinen Registry- oder Providerwrite aus.

Close-Fehler werden detailfrei technisch nicht verfügbar und ändern keinen
bereits committeten Fakt.

## Retention und Nichtwiederverwendung

Bootstrap-Request und Public Key bleiben mindestens bis zur eindeutigen
Bootstrap-Rekonstruktion und für alle erforderlichen Auditzeiträume gebunden.

Aktivierungsrequest, Challenge, Proof und Approval bleiben mindestens bis zum
eindeutigen Abschluss sowie für Incident-, Release- und Auditverweise erhalten.

Bootstrap-, Authority-, Key-, Change-, Revision-, Policy- und Reviewer-IDs
werden nie unter anderer Bedeutung wiederverwendet oder neu zugeordnet.

Persistente Decisions bleiben die normative Historie; lokale Dateien ersetzen
sie nicht.

## Bewusst nicht entschieden

LQ-278 entscheidet keine Python-Signatur, konkrete Verifierklasse,
Approval-Infrastruktur, HSM-, Agent-, KMS- oder Secret-Manager-Anbindung.

Es entscheidet keine neue Tabelle, SQL, Migration, Route, Settingsvariable,
Service-Unit, Scheduler-, CI-, Deployment- oder automatische Aktivierung.

Es erzeugt keinen privaten Key, signiert kein Release, promotet und
veröffentlicht nichts.

Die vollständige PostgreSQL-16-Pflichtsuite bleibt grün mit:

```text
3352 passed, 588 warnings
```

## Folgeordnung

LQ-279 sollte Proof- und Approval-Formate sowie die fest kontrollierte
Verifier-Composition entscheiden und implementieren.

Erst danach kann ein weiterer Slice beide owner-only Operatoren implementieren,
ohne Reviewer-Trust oder Kryptografie aus caller-gelieferten Dateien abzuleiten.
