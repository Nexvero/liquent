# LQ-237 — Detached Release Signature and Promotion Contract

## 1. Ergebnis

LQ-237 entscheidet den Sicherheitsvertrag zwischen einem lokal verifizierten,
unsignierten LQ-236-Kandidaten und einem autorisiert promotablem
Operationsbundle.

Eine detached Release-Signatur bestätigt, dass eine aktuell autorisierte
Release-Signing-Authority exakt die Checksummen eines technisch integren
Kandidaten freigegeben hat.

Sie veröffentlicht nichts, deployt nichts und autorisiert keine konkrete
Umgebung.

Dieser Slice implementiert keine Kryptografie, keine Schlüsselablage, keinen
Verifier und keine Promotion.

## 2. Drei getrennte Entscheidungen

Der Releasepfad besitzt drei unabhängige Entscheidungen:

1. LQ-236 bestätigt die technische Integrität des Kandidaten.
2. Eine Release-Signing-Authority signiert dessen exakte `SHA256SUMS`-Bytes.
3. Eine unabhängige Promotion-Prüfung löst Signer und Policy aktuell aus dem
   System of Record auf und entscheidet `promotable`.

Keine dieser Entscheidungen ersetzt eine andere.

## 3. Separate Release-Authority-Domäne

Release-Signing-Authority ist eine eigene Control-Plane-Domäne.

Sie ist ausdrücklich nicht abgeleitet aus:

- `SessionPrincipal` oder bloßer Authentifizierung;
- User- oder Workspace-Aktivität;
- gewöhnlicher Workspace-Mitgliedschaft;
- Research-Read- oder Research-Write-Permissions;
- Onboarding-, Membership-, Trust- oder Lifecycle-Management-Capabilities;
- Betriebssystembesitz einer lokalen Bundle-Datei;
- Build-, CI- oder Deploymentzugriff allein.

Ein Akteur kann mehrere getrennte Verantwortungen besitzen. Jede muss aber aus
ihrer eigenen maßgeblichen Authority-Quelle aufgelöst werden.

## 4. System of Record

Die Promotion-Prüfung verwendet eine kontrolliert verwaltete
Release-Authority-Registry als System of Record.

Sie bindet mindestens:

- eine stabile, niemals neu zugewiesene Signer-Authority-ID;
- eine stabile, niemals neu zugewiesene Key-ID;
- den kanonischen Fingerprint des öffentlichen Schlüssels;
- den erlaubten Signaturkontext;
- aktiven oder inaktiven Authority-Status;
- aktiven, abgelaufenen oder widerrufenen Key-Status;
- die aktuelle Policy-Revision.

Das Bundle, seine Signatur und caller-supplied Metadaten sind nicht dieses
System of Record.

## 5. Keine caller-supplied Autorisierung

Signing und Promotion akzeptieren niemals ein caller-supplied `allow`, eine
Rolle, Capability-Liste oder behauptete Signer-Aktivität.

Der Aufrufer darf ausschließlich Kandidat, detached Signatur und die zum
Lookup nötige stabile Key-Referenz vorlegen.

Die Entscheidung löst Authority, Key, Status, erlaubten Kontext und Policy
selbst aus der maßgeblichen Quelle auf.

## 6. Technisch integrer Kandidat als Voraussetzung

Signing beginnt nur, wenn der unveränderte LQ-236-Verifier erfolgreich war.

Der Signierpfad bestätigt vor Zugriff auf private Schlüssel erneut mindestens:

- exakten Archivnamen;
- Bundle-Formatversion 1;
- vollständigen Source-Commit;
- kanonisches Manifest;
- vollständige `SHA256SUMS`;
- alle Payload-Hashes;
- `integrity = verified`;
- `promotable = false` für den noch unsignierten Kandidaten.

Ein technischer Fehler oder unbekannter Inhalt erreicht den Signierschritt
nicht.

## 7. Signaturformat

Formatversion 1 verwendet eine detached SSHSIG-Signatur mit einem
Ed25519-Release-Schlüssel.

Der feste Signatur-Namespace lautet:

```text
liquent-operations-release-v1
```

Signiert werden exakt die im Archiv enthaltenen Bytes von `SHA256SUMS`, ohne
Normalisierung, Präfix, Zeilenumbruchänderung oder neu erzeugte Kopie.

Andere Namespaces, Algorithmen, Hashauswahlen oder eingebettete Signaturen sind
nicht austauschbar und werden fail-closed abgelehnt.

## 8. Externe Release-Dateien

Der Releasekanal hält nebeneinander:

```text
liquent-operations-<version>-<commit>.tar.gz
liquent-operations-<version>-<commit>.tar.gz.sshsig
liquent-operations-<version>-<commit>.promotion.json
```

Signatur und Promotion-Evidence werden nicht nachträglich in das bereits
gehashte Archiv eingebettet.

Keiner der drei Pfade darf überschrieben oder für andere Bytes wiederverwendet
werden.

## 9. Key-ID und Fingerprint

Die Key-ID dient nur als stabile Lookup-Referenz. Vertrauen entsteht erst durch
den aktuell aus dem System of Record geladenen öffentlichen Schlüssel und
dessen kanonischen Fingerprint.

Eine Key-ID wird niemals einem neuen Schlüssel zugewiesen. Ein Fingerprint
wird niemals einer anderen Signer-Authority zugerechnet.

Dateiname, Kommentar, E-Mail-Adresse oder frei formulierter Principal sind
keine Authority-Fakten.

## 10. Private Schlüssel

Private Release-Schlüssel verlassen ihren kontrollierten Signierkontext nicht.

Sie sind unzulässig in:

- Repository und Worktree;
- Bundle, Wheel, sdist oder Container;
- CI-Logs und Test-Fixtures;
- Request-, Resultat- oder Evidence-Dateien;
- Environment-Beispielen;
- Promotion-Registry und öffentlichem Releasekanal.

LQ-237 entscheidet nicht, ob der spätere Signierkontext Hardware, Agent oder
einen anderen kontrollierten Key-Provider verwendet.

## 11. Signer-Autorisierung

Eine Signatur ist nur autorisiert, wenn bei der Signierentscheidung:

- Signer-Authority und Key vorhanden sind;
- beide aktiv sind;
- der Key der Authority unverändert zugeordnet ist;
- der Namespace exakt erlaubt ist;
- die aktuelle Policy den Kandidaten zulässt;
- die technische Kandidatenprüfung erfolgreich ist.

Fehlende, inaktive, abgelaufene, widerrufene oder inkonsistente Fakten sperren
den Signiervorgang.

## 12. Unabhängige Promotion-Prüfung

Die Promotion-Prüfung wird von einem anderen kontrollierten Operator oder
einer organisatorisch getrennten Automation ausgeführt als der konkrete
Signiervorgang.

Sie vertraut keinem vom Signierprozess gelieferten Erfolgsboolean.

Sie führt selbst aus:

1. vollständigen LQ-236-Bundle-Verify;
2. Extraktion der exakten `SHA256SUMS`-Bytes nur in Memory;
3. aktuellen Authority- und Key-Lookup;
4. Fingerprint-, Algorithmus- und Namespace-Prüfung;
5. kryptografische SSHSIG-Verifikation;
6. aktuellen Policy- und Revocation-Lookup;
7. Erzeugung detailarmer Promotion-Evidence.

## 13. Promotion-Ergebnis

Nur wenn alle technischen und autoritativen Prüfungen erfolgreich sind, darf
das Ergebnis lauten:

```text
integrity = verified
signature = verified
authority = current
promotable = true
```

`promotable = true` bedeutet ausschließlich: Dieser unveränderte Kandidat darf
in einen separat autorisierten Releasekanal übernommen werden.

Es bedeutet weder deployed noch für eine konkrete Umgebung freigegeben.

## 14. Revocation wirkt auf spätere Entscheidungen

Jede Promotion-Prüfung liest Authority-, Key- und Policy-Status aktuell neu.

Nach committierter Deaktivierung oder Revocation muss jede spätere Prüfung
fail-closed enden, auch wenn dieselbe Signatur zuvor erfolgreich war.

Es gibt keinen dauerhaften positiven Authority-Cache und kein caller-supplied
`signed_at`, mit dem aktuelle Revocation umgangen werden kann.

## 15. Bereits promotete oder deployte Releases

Key-Revocation löscht keine historischen Fakten und schreibt keine bestehende
Evidence um.

Sie verhindert neue Promotion-Entscheidungen. Für bereits veröffentlichte oder
deployte Releases eröffnet sie zusätzlich einen expliziten Incident- und
Reassessment-Prozess.

Rollback, Quarantäne oder Weiterbetrieb sind separate autorisierte
Environment-Entscheidungen und werden nicht automatisch aus der
Key-Revocation abgeleitet.

## 16. Rotation

Rotation erzeugt immer eine neue Key-ID und einen neuen Fingerprint.

Ein kontrolliertes Überlappungsfenster darf mehrere aktive Keys derselben
Signer-Authority enthalten. Jede einzelne Signatur verwendet trotzdem genau
einen Key.

Nach Ende des Fensters wird der alte Key deaktiviert oder widerrufen. Er wird
weder gelöscht noch wieder aktiviert oder neu zugewiesen.

## 17. Compromise und Recovery

Bei vermutetem Schlüsselverlust oder Missbrauch gilt mindestens:

1. betroffenen Key im System of Record widerrufen;
2. neue Promotionen sofort sperren;
3. betroffene historische Promotionen über Fingerprint und Bundle-Hash finden;
4. Impact und Environmentbezug separat bewerten;
5. neuen Key mit neuer ID kontrolliert provisionieren;
6. Kandidaten nur nach erneuter unabhängiger Prüfung neu signieren.

Eine Ersatzsignatur überschreibt keine kompromittierte historische Signatur.

## 18. Neusignieren unveränderter Kandidaten

Ein byteidentischer Kandidat darf nach Rotation mit einem neuen autorisierten
Key erneut signiert werden.

Dabei entstehen eine neue detached Signatur und neue Promotion-Evidence. Das
Archiv und seine `SHA256SUMS` bleiben unverändert.

Alte und neue Signatur bleiben unterscheidbar und auditierbar. Die neue
Signatur verleiht der alten keine nachträgliche Gültigkeit.

## 19. Promotion-Evidence

Die detailarme `promotion.json` bindet mindestens:

- Evidence-Schema-Version;
- Bundle-Dateiname und SHA-256;
- SHA-256 der exakten `SHA256SUMS`-Bytes;
- SHA-256 der detached Signatur;
- vollständigen Source-Commit und Paketversion;
- Bundle-Formatversion;
- Signaturformat und Namespace;
- Signer-Authority-ID, Key-ID und Fingerprint;
- verwendete Policy-Revision;
- Ergebnis der technischen, kryptografischen und Authority-Prüfung;
- Identität der unabhängigen Verification-Automation oder des Operators;
- unveränderlichen Entscheidungszeitpunkt.

Sie enthält keine privaten Schlüssel, Credentials, DSNs, Hostpfade oder
internen Fehlerdetails.

## 20. Evidence ist kein Authority-System

Promotion-Evidence dokumentiert eine getroffene Entscheidung. Sie gewährt
keine Authority und ersetzt keinen aktuellen Lookup.

Kopieren, Editieren oder erneutes Vorlegen einer früher positiven Evidence
darf keine neue Promotion autorisieren.

Eine spätere Prüfung bindet erneut die aktuellen Registry-Fakten an exakt
dieselben Kandidaten-, Checksum- und Signaturbytes.

## 21. Fehlergrenze

Unbekannte oder inaktive Authority, unbekannter oder widerrufener Key,
Fingerprint-Mismatch, falscher Namespace, ungültige Signatur, beschädigtes
Bundle und technische Registry-Unverfügbarkeit führen nicht zu
`promotable = true`.

Nach außen bleibt die Ablehnung detailarm. Intern dürfen kontrollierte
Audit-Ereignisse kategorisieren, ob Integrität, Signatur, Authority oder
Infrastruktur betroffen war, ohne Schlüsselmaterial oder private Pfade zu
protokollieren.

Technische Unverfügbarkeit wird nicht als neutrale Abwesenheit oder ungültige
Signatur ausgegeben, gewährt aber ebenfalls keine Promotion.

## 22. Retention und Nichtwiederverwendung

Authority-, Key-, Revocation-, Policy- und Promotion-Fakten werden mindestens
so lange aufbewahrt, wie ein Release, Deployment, Rollback oder Audit auf sie
Bezug nehmen kann.

Stabile IDs, Fingerprints, Bundle-Namen, Signaturpfade und Evidence-Pfade
werden nie für andere Fakten oder Bytes wiederverwendet.

Deaktivierte und widerrufene Einträge bleiben als nicht autorisierende
historische Fakten erhalten.

## 23. Keine Selbstsignatur des Vertrauensankers

Ein im Bundle enthaltener öffentlicher Schlüssel, Fingerprint oder
Allowed-Signers-Eintrag darf informativ sein, ist aber niemals der
Vertrauensanker für seine eigene Prüfung.

Der Verifier erhält den Trust Root ausschließlich aus der kontrollierten
Release-Authority-Registry beziehungsweise ihrer unabhängig provisionierten
lokalen Projektion.

## 24. Verhältnis zum Releasekanal

Promotion erlaubt nur die atomare Aufnahme des unveränderten Tripels aus
Archiv, detached Signatur und Promotion-Evidence in einen kontrollierten
Releasekanal.

Der Kanal muss Immutable-Namen und Hashgleichheit durchsetzen. Teilweise
Publikation, Überschreiben und stiller Austausch einzelner Dateien sind
unzulässig.

Konkrete Registry-, Repository- oder Hostingtechnologie bleibt offen.

## 25. Bewusst nicht enthalten

LQ-237 entscheidet oder implementiert keine:

- Datenbank-, Tabellen-, SQL-, Migration- oder Portstruktur;
- konkrete Release-Authority-Registry-Implementierung;
- Key-Erzeugung, -Import, -Ablage oder Hardwarebindung;
- Signier- oder Verify-CLI;
- konkrete Person, Gruppe oder Organisation als Signer;
- Package-Version, Git-Tag oder Branch;
- Git-Staging-, Commit-, Push- oder Pull-Request-Aktion;
- Veröffentlichung, Registrymutation oder Deployment;
- automatische Rollback- oder Incidententscheidung.

## 26. Nächster Slice

LQ-238 sollte die lokale read-only SSHSIG-Verifikation und die kontrollierte
Release-Authority-Registry-Grenze implementieren.

Er muss Trust Root und Key-Status extern injizieren, Signatur-, Namespace- und
Fingerprintbindung prüfen, aktuelle Revocation fail-closed anwenden und
detailarme Promotion-Evidence erzeugen, ohne private Schlüssel, Signing,
Publikation oder Deployment in denselben Slice aufzunehmen.
