# LQ-239 — Release Signing Operator and Authority Lifecycle Contract

## 1. Ergebnis

LQ-239 entscheidet den Vertrag für kontrolliertes Release-Signing und den
Lifecycle der in LQ-237/238 verwendeten Release-Authority-Registry.

Der Vertrag trennt:

- technische Bundle-Integrität;
- Release-Signing-Authority;
- Registry-Lifecycle-Authority;
- unabhängige Promotion-Verifikation;
- Veröffentlichung und Deployment.

Dieser Slice implementiert keine Registry, Persistenz, Kryptografie, CLI,
Schlüsselmutation, Signatur oder Promotion.

## 2. Zwei getrennte Authority-Domänen

Release-Signing-Authority darf einen technisch integren Kandidaten mit genau
einem ihr aktuell zugeordneten aktiven Key signieren.

Release-Registry-Lifecycle-Authority darf Signer-Authorities, öffentliche
Keys, Status und Policy-Revisionen kontrolliert verwalten.

Keine der beiden Authorities impliziert die andere.

## 3. Keine Produktrolle

Beide Release-Authorities sind unabhängig von:

- `SessionPrincipal` oder bloßer Authentifizierung;
- interner UserId und WorkspaceId;
- gewöhnlicher Workspace-Mitgliedschaft;
- Research-Permissions;
- Onboarding-, Membership-, Trust- oder User-/Workspace-Lifecycle-Authority;
- Git-, CI-, Betriebssystem-, Datenbank- oder Deploymentzugriff;
- Besitz einer Bundle-, Registry- oder privaten Schlüsseldatei.

Produkt- und Release-Control-Plane bleiben strukturell getrennt.

## 4. Maßgebliches System of Record

Die Release-Authority-Registry ist das System of Record für:

- stabile Signer-Authority-IDs;
- stabile Registry-Lifecycle-Authority-IDs;
- stabile Key-IDs und Fingerprints;
- öffentliche Schlüssel und erlaubte Namespaces;
- Authority- und Key-Status;
- vollständige Registry-Set-Revisionen;
- Policy-Revisionen;
- Lifecycle-, Signing- und Recovery-Entscheidungen.

JSON-Projektionen für LQ-238 sind read-only Exporte, nicht selbst die
maßgebliche Registry.

## 5. Stabile interne Fakten

Signer-Authority-ID, Registry-Lifecycle-Authority-ID, Key-ID,
Registry-Set-Revision, Signing-Decision-ID, Lifecycle-Change-ID und
Recovery-ID sind intern erzeugte, nicht erratbare und nicht wiederverwendbare
Fakten.

Keine ID wird aus E-Mail-Adresse, Username, Fingerprint, Zeit, Bundle-Hash oder
Environmentnamen abgeleitet.

Deaktivierte oder widerrufene Fakten behalten ihre ursprüngliche Bedeutung.

## 6. Registry-Set-Revision

Jede committete Registry-Konfiguration besitzt genau eine aktuelle stabile
Set-Revision.

Sie bezeichnet den vollständigen Bestand aus:

- Signing-Authorities und Status;
- Lifecycle-Authorities und Status;
- Keys, Zuordnungen und Status;
- Namespace- und Algorithmusbindungen;
- aktueller Release-Policy.

Jede reguläre Mutation verlangt die exakt erwartete aktuelle Revision und
erzeugt atomar eine neue, niemals wiederverwendete Revision.

## 7. Kein caller-supplied Authority-Satz

Ein Aufrufer liefert ausschließlich eine eng begrenzte Änderungsabsicht,
Zielreferenzen, stabile Change-ID und erwartete Revision.

Er liefert niemals:

- `allow` oder `authorized`;
- Rollen- oder Capability-Listen;
- vollständigen Registry-Snapshot;
- behauptete aktuelle Statuswerte;
- resultierende Revision;
- fremde Authority-Zuordnung;
- private Schlüsselbytes.

Die Schreibgrenze löst alle aktuellen Fakten selbst auf.

## 8. Reguläre Lifecycle-Autorisierung

Für jede neue reguläre Mutation bestätigt dieselbe atomare Schreibgrenze:

1. Lifecycle-Actor existiert und ist aktiv;
2. Actor besitzt aktuell Registry-Lifecycle-Authority;
3. Ziel-Authority oder Ziel-Key gehört zur erwarteten Domäne;
4. erwartete Registry-Set-Revision ist aktuell;
5. Transition und Separation of Duties sind zulässig;
6. Change-ID wurde nicht widersprüchlich wiederverwendet.

Ein vorher aufgelöstes Token, Environment-Flag oder CLI-Erfolgsboolean ersetzt
diese Entscheidung nicht.

## 9. Signer-Authority-Lifecycle

Regulär zulässige Absichten für Signer-Authorities sind:

- `GRANT`: neue Signer-Authority ohne frühere Historie anlegen;
- `DEACTIVATE`: aktive Signer-Authority inaktiv setzen;
- `REACTIVATE`: historische inaktive Signer-Authority reaktivieren.

Es gibt kein Löschen, Umbenennen, Transferieren oder Upsert unter bestehender
ID.

Reaktivierung einer Authority reaktiviert keinen ihrer Keys automatisch.

## 10. Lifecycle-Authority-Lifecycle

Registry-Lifecycle-Authorities verwenden dieselben drei expliziten Absichten:
`GRANT`, `DEACTIVATE` und `REACTIVATE`.

Reguläre Deaktivierung darf nie den letzten aktuell wirksamen
Lifecycle-Manager entfernen.

Vor Selbstdeaktivierung muss mindestens ein anderer wirksamer Manager
existieren. Prüfung und Statusänderung erfolgen in derselben Transaktion.

## 11. Key-Provisionierung

Ein neuer Key wird zunächst als inaktiver Registry-Fakt registriert.

Die Provisionierung bindet atomar:

- neue Key-ID;
- genau eine bestehende Signer-Authority;
- Algorithmus `ssh-ed25519`;
- Namespace `liquent-operations-release-v1`;
- kanonischen Public Key;
- unabhängig berechneten kanonischen Fingerprint;
- neue Registry-Set-Revision;
- persistente Lifecycle-Entscheidung.

Private Schlüssel oder Provider-Credentials erreichen die Registry nicht.

## 12. Proof of Possession

Vor Aktivierung muss der kontrollierte Key-Provider einen einmaligen,
registryerzeugten Challenge-Kontext mit dem neuen privaten Schlüssel
signieren.

Die Registry-Grenze prüft den Nachweis gegen den bereits gebundenen Public Key,
Fingerprint, Algorithmus und einen dedizierten Provisionierungs-Namespace.

Der Challenge-Nachweis ist keine Release-Signatur und kann keinen Kandidaten
promoten.

Konkretes Challenge-Format und Kryptografieadapter bleiben dem
Implementierungsslice vorbehalten.

## 13. Key-Aktivierung

Aktivierung ist eine separate Lifecycle-Entscheidung nach erfolgreicher
Provisionierung und Proof of Possession.

Sie verlangt:

- aktive zugeordnete Signer-Authority;
- inaktiven, noch nie widerrufenen Key;
- bestätigten unveränderten Public Key und Fingerprint;
- aktuelle erwartete Registry-Set-Revision;
- neue stabile Lifecycle-Change-ID;
- unabhängigen Review gemäß Separation of Duties.

Aktivierung erzeugt eine neue Registry-Set-Revision.

## 14. Key-Deaktivierung und Expiry

Deaktivierung ist eine geplante reversible Betriebsentscheidung.

Expiry ist ein fail-closed wirksamer zeitlicher oder explizit materialisierter
Status. Ein abgelaufener Key kann keine spätere Signing- oder
Promotion-Entscheidung tragen.

Reaktivierung eines nur deaktivierten Keys benötigt eine explizite eigene
Transition. Ein abgelaufener Key wird nicht verlängert oder reaktiviert,
sondern durch einen neuen Key ersetzt.

## 15. Key-Revocation

Revocation ist permanent und nicht umkehrbar.

Sie ist zulässig bei Verlust, vermutetem Missbrauch, Providerkompromittierung,
falscher Zuordnung oder Security-Entscheidung.

Eine Key-ID, ihr Fingerprint und Public Key bleiben historisch erhalten. Der
Key kann weder reaktiviert noch einer anderen Authority zugewiesen werden.

## 16. Sofortige Wirkung

Nach Commit einer Authority-Deaktivierung, Key-Deaktivierung, Expiry,
Revocation oder Policy-Sperre müssen alle später begonnenen Signing- und
Promotion-Entscheidungen fail-closed enden.

Signing-Operator und LQ-238-Verifier lesen den aktuellen Bestand für jeden
neuen Vorgang erneut.

Es gibt keinen positiven Authority-Cache, Grace-Boolean oder caller-supplied
Zeitpunkt zur Umgehung des aktuellen Status.

## 17. Rotation

Rotation ist kein Überschreiben eines Keys.

Die kontrollierte Reihenfolge lautet:

1. neuen Key mit neuer ID inaktiv provisionieren;
2. Public Key und Fingerprint unabhängig prüfen;
3. Proof of Possession bestätigen;
4. neuen Key aktivieren;
5. Testkandidaten signieren und unabhängig verifizieren;
6. alten Key deaktivieren oder bei Risiko widerrufen.

Ein begrenztes Überlappungsfenster mit mehreren aktiven Keys ist zulässig und
in der Registry explizit sichtbar.

## 18. Signing-Request

Der kontrollierte Signing-Operator erhält ausschließlich:

- lokalen Pfad zum unveränderten Kandidaten;
- neue stabile Signing-Decision-ID;
- ausgewählte stabile Key-ID;
- exakt erwartete aktuelle Registry-Set-Revision;
- neuen abwesenden Signatur- und Decision-Evidence-Pfad;
- kontrolliert injizierten Key-Provider-Handle.

Er akzeptiert keine Authority-ID, Public-Key-Datei, Fingerprint-, Namespace-,
Algorithmus-, Allow- oder Promotion-Eingabe vom Caller.

## 19. Signing-Vorbedingungen

Vor Zugriff auf den privaten Key bestätigt der Signing-Operator:

1. vollständige LQ-236-Integrität des unveränderten Bundle-Snapshots;
2. neue oder exakt wiederholte Signing-Decision-ID;
3. aktuelle erwartete Registry-Set-Revision;
4. aktive Signer-Authority des ausgewählten Keys;
5. aktiven, nicht abgelaufenen und nicht widerrufenen Key;
6. festen Algorithmus und Release-Namespace;
7. Key-Provider-Fingerprint entspricht der Registry;
8. aktuelle Policy erlaubt diesen Kandidaten.

Erst danach werden die exakten `SHA256SUMS`-Bytes signiert.

## 20. Persistente Signing-Entscheidung

Jeder Signiervorgang besitzt eine persistente unveränderliche Entscheidung.

Sie bindet mindestens:

- Signing-Decision-ID;
- Bundle-, `SHA256SUMS`- und Signaturhash;
- vollständigen Source-Commit und Paketversion;
- Signer-Authority-ID, Key-ID und Fingerprint;
- Registry-Set- und Policy-Revision;
- Signaturformat und Namespace;
- kontrollierte Signing-Executor-Identität;
- Entscheidungszeit und erfolgreiches Ergebnis.

Sie enthält keinen privaten Key, Provider-Token, DSN oder Hostpfad.

## 21. Atomarer Signing-Output

Signaturdatei und geschützte Signing-Decision-Evidence werden zuerst unter
eindeutig besessenen temporären Namen erzeugt.

Der Vorgang gilt erst als erfolgreich, wenn:

- die Signatur gegen Registry-Public-Key und exakte Checksumbytes lokal
  verifiziert wurde;
- die persistente Signing-Entscheidung committet ist;
- beide finalen Outputpfade exklusiv und vollständig materialisiert sind.

Vorhandene Zielpfade werden nie überschrieben.

Der konkrete Commit-/Filesystem-Koordinationsmechanismus bleibt späterer
Implementierung vorbehalten und darf keinen halben Erfolg als abgeschlossen
melden.

## 22. Exakte technische Wiederholung

Nach unklarem Ausgang wird exakt dieselbe Signing-Decision-ID mit identischem
Bundle-Hash, Key, erwarteter Revision und Output-Inhalt wiederholt.

Eine bereits committete identische Entscheidung liefert dieselben gebundenen
Signatur- und Evidence-Bytes beziehungsweise deren unveränderliche
Wiederherstellung, ohne neue Authority-Prüfung oder zweite Entscheidung.

Wiederverwendung derselben ID mit anderem Kandidaten, Key, Revision oder
Kontext ist ein detailarmer Konflikt.

## 23. Konkurrenz

Für eine neue Signing-Entscheidung werden Registry-Revision, Authority- und
Key-Status, Policy und persistente Decision in eine normative Reihenfolge
gebracht.

Gleichzeitige Deaktivierung oder Revocation gewinnt entweder vor Signing und
sperrt es oder wird sichtbar danach committet. Es darf keinen Zustand geben,
in dem Signing auf stale Authority committet, obwohl Revocation bereits vorher
normativ wirksam war.

Spätere Revocation sperrt unabhängig davon jede neue LQ-238-Promotion-Prüfung.

## 24. Separation of Duties

Mindestens folgende Identitäten müssen pro Releaseentscheidung getrennt sein:

- konkrete Signing-Executor-Identität;
- unabhängige Promotion-Verification-Identität.

Registry-Lifecycle-Änderungen an eigener Authority oder eigenem Key benötigen
zusätzlich unabhängige Freigabe und dürfen nicht durch alleinigen Besitz des
betroffenen privaten Keys autorisiert werden.

Build-, Signing-, Verification- und Deployment-Evidence bleiben getrennt
zuordenbar. Eine einzelne positive Evidence ersetzt keine zweite Funktion.

## 25. Kein Signing-Lockout-Schutz

Security-Revocation darf nicht blockiert werden, nur weil danach kein aktiver
Signing-Key verbleibt.

Im Zweifel hat Sperrung Vorrang vor Release-Verfügbarkeit. Ein Scope ohne
aktiven Signing-Key kann nicht signieren, bleibt aber sicher geschlossen.

Nur der letzte wirksame Registry-Lifecycle-Manager ist gegen reguläre
Deaktivierung geschützt.

## 26. Einmaliger Bootstrap

Der initiale Registry-Bootstrap ist ein eigener späterer Slice.

Er darf atomar genau folgende ersten Fakten erzeugen:

- erste Registry-Lifecycle-Authority;
- erste Signer-Authority;
- ersten inaktiven Public-Key-Fakt;
- erste Registry-Set- und Policy-Revision;
- unveränderliche Bootstrap-Entscheidung.

Key-Aktivierung bleibt auch danach eine separate Proof-of-Possession- und
Review-Entscheidung. Bootstrap signiert keinen Release.

Sobald irgendeine Registry-Historie existiert, bleibt Bootstrap dauerhaft
geschlossen.

## 27. Reguläre Recovery

Recovery ist kein Re-Bootstrap und keine beliebige Neuwahl eines Managers.

Sie ist nur zulässig, wenn Registry-Historie existiert, aber keine bestehende
aktive Lifecycle-Authority mehr wirksam ist.

Recovery darf ausschließlich eine historisch bereits gebundene inaktive
Lifecycle-Authority reaktivieren. Sie darf keine Signer-Authority und keinen
Key aktivieren, keinen neuen Public Key registrieren und keinen Release
signieren.

## 28. Emergency Revocation

Key-Revocation benötigt einen getrennten owner-only Notfallpfad, falls
reguläre Lifecycle-Authority nicht rechtzeitig verfügbar ist.

Dieser Pfad darf ausschließlich einen bereits bekannten Key unwiderruflich
widerrufen und eine neue Registry-Set-Revision erzeugen.

Er darf keinen Key, Signer oder Lifecycle-Manager erzeugen, aktivieren,
reactivieren oder umhängen. Exakte erwartete Revision, stabile Emergency-ID,
unabhängige Freigabe und unveränderliche Entscheidung bleiben verpflichtend.

## 29. Recovery- und Emergency-Retry

Jede Recovery- oder Emergency-Revocation besitzt eine stabile, niemals
wiederverwendete domänenspezifische ID.

Exakte Wiederholung derselben ID und desselben Inputs liefert die bereits
committete Ergebnisrevision ohne zweite Mutation.

Abweichende Wiederverwendung ist ein detailarmer Konflikt.

## 30. Fehlergrenzen

Unbekannte oder inaktive Authority, unbekannter Key, stale Revision,
unzulässige Transition, fehlender Proof of Possession, Lockout-Verstoß oder
nicht bestätigte Separation of Duties ergeben dieselbe detailarme fachliche
Ablehnung.

Konstante ID mit anderem Inhalt ist ein eigener detailarmer Konflikt.

Registry-, Transaktions-, Key-Provider-, Kryptografie-, Dateisystem- oder
Strukturfehler sind getrennte detailarme technische Nichtverfügbarkeit.

Keine Ausgabe enthält private Schlüssel, Provider-Handles, Registry-Inventar,
IDs anderer Authorities, interne Pfade, SQL, DSN oder ursprüngliche
Fehlerdetails.

## 31. Retention und Nichtwiederverwendung

Authority-, Key-, Revision-, Lifecycle-, Signing-, Recovery- und Emergency-
Entscheidungen werden mindestens so lange aufbewahrt, wie irgendein Release,
Deployment, Rollback, Incident oder Audit auf sie verweist.

IDs, Fingerprints, Public Keys, Revisionen und Decision-Evidence werden nie
gelöscht und unter neuer Bedeutung wiederverwendet.

Private Key-Retention und sichere Vernichtung gehören dem kontrollierten
Key-Provider und dürfen die öffentlichen historischen Fakten nicht verändern.

## 32. Operatorgrenze

Lifecycle-, Signing-, Recovery- und Emergency-Operationen bleiben getrennte
owner-only Offline-Commands mit getrennten Request-Shapes und Credentials.

Sie sind keine HTTP-Routen, Startup-Hooks, Deployment-Schritte oder
automatischen CI-Seiteneffekte.

Requests, Provider-Handles, Registryzugang und Resultate werden niemals in
Shell-History, Logs, Chat, Tickets, Images oder Bundle-Payload aufgenommen.

## 33. Bewusst nicht enthalten

LQ-239 entscheidet oder implementiert keine:

- Python-Modelle, Ports, Exceptions oder Signaturen;
- Datenbank-, Tabellen-, SQL-, Migration- oder Locking-Struktur;
- Registry- oder Signing-Adapter;
- konkrete Key-Provider-, HSM-, Agent- oder Credentialtechnologie;
- Bootstrap-, Lifecycle-, Signing-, Recovery- oder Emergency-CLI;
- öffentliche oder private Schlüssel;
- Package-Version, Git-Tag oder Releasekanal;
- Veröffentlichung, Promotion, Deployment oder Rollback;
- Git-Staging-, Branch-, Commit-, Push- oder Pull-Request-Aktion.

## 34. Nächster Slice

LQ-240 sollte die persistente Release-Authority-Registry-Foundation und
stabilen Revision-/Decision-Typen implementieren.

Er muss additive, historienerhaltende Persistenz für Authorities, Public Keys,
Registry-Revisionen und Lifecycle-/Signing-Entscheidungen schaffen, ohne Seed,
Bootstrap, Key-Aktivierung, Signing, Recovery, Operator oder Production-Wiring
in denselben Slice aufzunehmen.
