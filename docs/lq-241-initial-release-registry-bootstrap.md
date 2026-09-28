# LQ-241 — Initial Release Registry Bootstrap

## 1. Ergebnis

LQ-241 implementiert den einmaligen persistenten Bootstrap der
Release-Authority-Registry.

Eine erfolgreiche atomare Entscheidung erzeugt exakt:

- erste aktive Registry-Lifecycle-Authority;
- erste aktive Release-Signer-Authority;
- ersten unveränderlichen Public-Key-Fakt;
- denselben Key im Status `inactive`;
- erste aktive Policy-Revision;
- erste vollständige Registry-Set-Revision;
- aktuellen Singleton-Pointer;
- unveränderliche Bootstrap-Entscheidung.

Der Bootstrap aktiviert keinen Key und signiert keinen Release.

## 2. Eigene Bootstrap-Identität

LQ-241 ergänzt `ReleaseRegistryBootstrapId` als zehnten stabilen
Release-Control-Plane-ID-Typ.

Die ID ist frozen, slotted, repr-frei und wird durch den bestehenden sicheren
Materialgenerator aus einem unabhängigen Zug von mindestens 32 Byte
Betriebssystementropie erzeugt.

Sie ist keine Authority und enthält keinen Public-Key- oder Environmentbezug.

## 3. Warum caller-stabil

Der Offline-Aufrufer bewahrt genau eine Bootstrap-ID für die geprüfte
Initialentscheidung.

Nach Timeout, verlorenem Resultat oder unklarem Commit-Ausgang wird dieselbe ID
mit demselben Public-Key-Material wiederholt.

Ohne diese stabile ID könnte ein bereits committeter Bootstrap nur als
geschlossen erscheinen und seine intern erzeugten Authority-/Revision-IDs
nicht sicher zurückgeben.

## 4. Public-Key-Modell

`ReleaseSigningPublicKey` bindet ausschließlich:

- kanonischen `SHA256:`-Fingerprint;
- einzeiligen kommentarfreien `ssh-ed25519` Public Key.

Beide Felder sind repr-frei. Newlines, fremde Algorithmen, Kommentare und
strukturell ungültige Fingerprints werden an der Modellgrenze abgelehnt.

Private Schlüssel oder Provider-Handles sind nicht darstellbar.

## 5. Ergebnisobjekt

`BootstrappedReleaseRegistry` liefert:

- Bootstrap-ID;
- Lifecycle-Authority-ID;
- Signer-Authority-ID;
- Key-ID;
- Registry-Set-Revision-ID;
- Policy-Revision-ID.

Alle IDs bleiben im `repr` verborgen. Das Ergebnis enthält weder Public Key
noch Fingerprint, Registry-Inventar oder private Details.

## 6. Portgrenze

`InitialReleaseRegistryBootstrap.bootstrap` akzeptiert exakt:

```text
bootstrap_id
public_key
```

Die Signatur enthält keinen Actor, `SessionPrincipal`, Authority-Identifier,
Key-Identifier, resultierende Revision, Status, Rolle, Capability oder
caller-supplied Allow-Wert.

Alle resultierenden IDs werden innerhalb der atomaren Entscheidung erzeugt.

## 7. Additive Migration

Revision `20260817_0018` baut linear auf `20260817_0017` auf und ergänzt
ausschließlich `release_registry_bootstraps`.

Die Tabelle bindet Bootstrap-ID, beide Authorities, Key samt
Signer-Zuordnung sowie Registry- und Policy-Revision über Fremdschlüssel.

Sie erzeugt keine Seed-Zeile. Nach Migration bleibt die gesamte Registry leer.

## 8. Vollständige Leere als Voraussetzung

Ein neuer Bootstrap ist nur zulässig, wenn alle Release-Inventare leer sind:

- Signer-Authorities;
- Registry-Lifecycle-Authorities;
- Signing-Keys;
- Registry-Revisionen und alle Member;
- Current-Pointer;
- Lifecycle-Changes;
- Signing-Decisions;
- Bootstrap-Decisions.

Schon eine einzelne sichtbare Zeile schließt einen neuen Bootstrap.

## 9. Keine Teilbestandsadoption

Der Bootstrap adoptiert keinen manuellen, importierten oder teilweise
geschriebenen Registry-Bestand.

Eine vorhandene Authority ohne Revision, ein Pointer ohne unterstützte
Bootstrap-Entscheidung oder irgendein anderer Teilbestand führt zu neutralem
geschlossenem Bootstrap, nicht zu Ergänzung oder Reparatur.

Technische Strukturfehler während einer Abfrage bleiben detailarme
Nichtverfügbarkeit.

## 10. Aktive erste Lifecycle-Authority

Die erste Registry-Lifecycle-Authority wird im ersten vollständigen Snapshot
als `active` gespeichert.

Sie ist ausschließlich Grundlage für spätere kontrollierte Registry-
Lifecycle-Mutationen.

Sie gewährt keine Produkt-, Signing-, Promotion- oder Deployment-Authority.

## 11. Aktive erste Signer-Authority

Die erste Signer-Authority ist im ersten Snapshot `active`.

Das allein erlaubt noch kein Signing: Der einzige gebundene Key bleibt
inaktiv, bis ein späterer Proof-of-Possession- und Aktivierungsslice ihn
explizit aktiviert.

Signer-Authority und Registry-Lifecycle-Authority bleiben getrennte IDs.

## 12. Inaktiver erster Key

Der Public Key wird unveränderlich mit neuer Key-ID, erster
Signer-Authority-ID, Algorithmus, festem Release-Namespace, Fingerprint und
Public-Key-Text gebunden.

Sein Status im ersten vollständigen Registry-Snapshot ist exakt `inactive`.

Bootstrap kann ihn weder aktivieren noch einen Proof of Possession behaupten.

## 13. Erste Policy

Die intern erzeugte erste Policy-Revision wird im Registry-Snapshot als
`active` gebunden.

Dies bedeutet nur, dass eine gültige Basispolicy existiert. Wegen des
inaktiven Keys bleibt Signing weiterhin fail-closed.

Der Aufrufer liefert keine Policy-ID und keinen Policy-Status.

## 14. Vollständiger Snapshot

Die erste Registry-Set-Revision enthält exakt:

- eine aktive Lifecycle-Authority;
- eine aktive Signer-Authority;
- einen derselben Signer-Authority zugeordneten inaktiven Key;
- eine aktive Policy-Revision.

Der Current-Pointer wird in derselben Transaktion auf diese Revision gesetzt.

## 15. Atomare Reihenfolge

Innerhalb einer Datenbanktransaktion werden geordnet:

1. PostgreSQL-Tabellenlock beziehungsweise unterstützte SQLite-Transaktion;
2. exakter Retry-Lookup;
3. vollständige Leerheitsprüfung;
4. Erzeugung und Typprüfung aller fünf resultierenden IDs;
5. beide Authority-Existenzfakten;
6. unveränderlicher Public-Key-Fakt;
7. Revision und drei vollständige Member;
8. Current-Pointer;
9. Bootstrap-Decision.

Alles committet oder nichts.

## 16. Exakter Retry

Eine bereits vorhandene Bootstrap-ID wird vor der allgemeinen
History-Sperre aufgelöst.

Stimmen Fingerprint und Public Key exakt und ist der ursprüngliche
Bootstrap-Snapshot strukturell kanonisch, werden dieselben sechs Ergebnis-IDs
ohne Generatorzug und ohne zweite Mutation zurückgegeben.

Der Retry bleibt dadurch auch nach einem unklaren ersten Commit sicher.

## 17. Konflikt

Dieselbe Bootstrap-ID mit anderem Fingerprint oder Public Key ist
`ReleaseRegistryBootstrapConflict`.

Die Exception ist detailfrei und enthält weder Bootstrap-ID noch Keymaterial
oder gespeicherten Bestand.

Der Konflikt überschreibt und ergänzt nichts.

## 18. Dauerhaft geschlossener Bootstrap

Eine andere Bootstrap-ID nach irgendeiner sichtbaren Registry-Historie liefert
neutral `None`.

Generatoren werden in diesem Fall nicht aufgerufen. Deaktivierung, Revocation,
Verlust aller Keys oder Verlust aller Lifecycle-Manager öffnen Bootstrap nie
wieder.

Diese Zustände gehören Lifecycle, Recovery oder Emergency Revocation.

## 19. Konkurrenz

PostgreSQL serialisiert konkurrierende Bootstrap-Versuche über denselben
geordneten Tabellenlock.

Bei zwei verschiedenen Bootstrap-IDs committet exakt eine vollständige
Registry. Der zweite Vorgang sieht danach Historie und endet neutral.

Es entstehen niemals zwei Current-Pointer, zwei erste Keys oder gemischte
Snapshots.

## 20. Generatorfehler

Lifecycle-, Signer-, Key-, Registry- und Policy-ID werden erst nach bestätigter
Leere gezogen und auf ihren exakten Typ geprüft.

Fehler oder falscher Typ an jeder Generatorposition rollen alle bereits in der
Transaktion erzeugten Fakten zurück.

Der Aufrufer erhält ausschließlich detailarme technische Nichtverfügbarkeit.

## 21. Fehlergrenze

LQ-241 trennt:

- neutral geschlossenes Bootstrap als `None`;
- abweichende Wiederverwendung derselben ID als detailfreien Konflikt;
- Datenbank-, Generator-, Encoding-, Constraint- und Strukturfehler als
  `ReleaseRegistryBootstrapUnavailable`.

Keine Exception enthält IDs, Fingerprints, Keys, Tabellen, SQL, DSN oder
ursprüngliche Fehlerdetails.

## 22. Kein Signing oder Lifecycle-Change

Nach erfolgreichem Bootstrap bleiben
`release_signing_decisions` und `release_registry_lifecycle_changes` leer.

Es wird keine SSHSIG-Datei erzeugt, kein Key-Provider aufgerufen und keine
LQ-238-Promotion-Evidence erstellt.

Der HTTP-Prozess importiert oder aktiviert die Bootstrap-Grenze nicht.

## 23. Bundle-Head

Der LQ-236-Builder erwartet nun achtzehn lineare Migrationen und den einzigen
Head `20260817_0018`.

Das synthetische Test-Wheel enthält beide Release-Registry-Migrationen in der
korrekten linearen Reihenfolge.

## 24. Nachweis

SQLite-Tests belegen Portshape, kanonischen Erstbestand, exakten Retry,
Konflikt, dauerhafte History-Sperre, Teilbestandsperre, vollständigen Rollback
für jede Generatorposition und detailarme technische Fehler.

PostgreSQL-Tests belegen konkurrierende unterschiedliche Bootstrap-IDs sowie
exakte Retry-Auflösung im normativen Mehrprozess-Persistenzsystem.

Die vollständige Suite einschließlich aller PostgreSQL-Pflichttests besteht:

```text
2987 passed, 53 warnings
```

Der temporäre PostgreSQL-16-Cluster wurde kontrolliert gestoppt und vollständig
entfernt.

## 25. Retention und Nichtwiederverwendung

Bootstrap-ID, beide Authority-IDs, Key-ID, Registry- und Policy-Revision sowie
der Public-Key-Fakt werden nie gelöscht oder unter neuer Bedeutung
wiederverwendet.

Die Bootstrap-Decision bleibt mindestens so lange erhalten, wie Registry,
Signing, Promotion, Deployment, Recovery, Incident oder Audit darauf verweisen
kann.

## 26. Bewusst nicht enthalten

LQ-241 implementiert oder vollzieht keine:

- Key-Aktivierung oder Proof of Possession;
- reguläre Registry-Lifecycle-Mutation;
- Signing- oder Promotion-Entscheidung;
- Recovery oder Emergency Revocation;
- Registry-Projektion für LQ-238;
- Operator-CLI, Request-/Resultatdatei oder Key-Provider;
- Route, Settings, Startup- oder Production-Wiring;
- Git-Staging-, Branch-, Commit-, Push- oder Pull-Request-Aktion;
- Veröffentlichung oder Deployment.

## 27. Nächster Slice

LQ-242 sollte kontrollierten Proof of Possession und die Aktivierung des
initial inaktiven Release-Keys implementieren.

Er muss Challenge, Key-Provider-Fingerprint, aktuelle Lifecycle-Authority,
erwartete Registry-Revision, unabhängige Freigabe und exakten Retry atomar
binden, ohne bereits einen Release zu signieren oder zu promoten.
