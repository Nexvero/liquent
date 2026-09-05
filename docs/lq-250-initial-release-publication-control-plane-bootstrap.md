# LQ-250 — Initial Release Publication Control-Plane Bootstrap

## Ergebnis

LQ-250 implementiert den einmaligen atomaren Bootstrap der persistenten
Publication-Control-Plane aus LQ-249.

Ein erfolgreicher Erstaufruf erzeugt genau einen aktiven Channel, eine aktive
Publisher-Authority, eine vollständige Channel-Revision, ihren Current-Pointer
und eine unveränderliche Bootstrap-Entscheidung.

Er erzeugt keinen Handoff, kein Receipt und keinen Upload.

## Stabile Bootstrap-ID

`ReleasePublicationBootstrapId` ist ein eigener repr-freier, immutable und
geslotteter Typ.

Die sichere Materialerzeugung zieht für diese ID unabhängig mindestens 32
Byte Betriebssystementropie. Die ID wird nicht aus Channel, Provider,
Zielname, Actor, Zeit oder Environment abgeleitet.

Eine Bootstrap-ID gewährt selbst keine Publisher-Authority.

## Kontrollierte Channel-Definition

`ReleasePublicationChannelDefinition` bindet exakt:

- Paketname;
- Providerart;
- kanonischen Zielnamen.

Alle drei Werte müssen explizite nicht leere Strings sein. Die feste
Artefaktklasse `operational_bundle` ist kein Callerfeld, sondern wird von der
Persistenzgrenze gesetzt.

Credentials, Tokens, Clients, Allow-Werte und behauptete Authority-IDs sind
keine Definitionseingaben.

## Geschlossener Port

Der Bootstrap-Port akzeptiert ausschließlich:

- caller-stabile `ReleasePublicationBootstrapId`;
- kontrollierte `ReleasePublicationChannelDefinition`.

Publisher-Authority-ID, Channel-ID und Channel-Policy-Revision entstehen erst
innerhalb der atomaren Grenze über typisierte sichere Generatoren.

Der Caller liefert keine Rolle, Capability, resultierende IDs, Current-
Revision, Statuswerte oder vollständigen Snapshot.

## Atomarer Erstbestand

Ein erfolgreicher Bootstrap persistiert in einer Transaktion:

1. stabile Publisher-Authority;
2. stabilen Publication-Channel;
3. aktive Channel-Revision;
4. aktiven Publisher-Member derselben Revision;
5. Current-Pointer desselben Channels;
6. unveränderliche Bootstrap-Entscheidung.

Channel-Revision und Bootstrap binden dieselbe Paket-, Provider- und
Zieldefinition.

## Resultat

`BootstrappedReleasePublicationControlPlane` enthält ausschließlich:

- Bootstrap-ID;
- Publisher-Authority-ID;
- Channel-ID;
- Channel-Policy-Revision-ID.

Alle Felder sind repr-frei. Das Resultat enthält keine Credentials,
Providerhandles, DSN, Pfade oder Handoff-/Publicationentscheidung.

## Persistente Bootstrap-Entscheidung

Migration `20260817_0021` ergänzt
`release_publication_bootstraps`.

Jede Zeile bindet Bootstrap-ID, erzeugte Publisher-Authority, Channel,
Channel-Revision sowie die exakte Paket-, Provider- und Zieldefinition.

Composite Foreign Keys verhindern, dass eine Bootstrap-Entscheidung eine
Revision eines anderen Channels referenziert.

## Nur einmal

Vor jeder neuen Erzeugung prüft dieselbe Transaktion alle neun Publication-
Inventare:

- Channels;
- Publisher-Authorities;
- Channel-Revisionen;
- Revision-Publisher;
- Current-Pointer;
- Handoffs;
- Receipts;
- Reassessments;
- Bootstrap-Entscheidungen.

Sobald irgendeine sichtbare Historie existiert, kann keine andere
Bootstrap-ID einen zweiten Erstbestand erzeugen.

Auch fremder Teilbestand schließt Bootstrap dauerhaft fail-closed.

## Exakter Retry

Ein Retry derselben Bootstrap-ID und derselben Channel-Definition liefert
dieselben vier stabilen IDs.

Dabei werden Publisher-, Channel- und Revisionsgenerator nicht erneut
aufgerufen. Es entsteht keine zweite Mutation und kein neuer Current-Pointer.

Die Persistenzgrenze verifiziert beim Retry zusätzlich aktive Revision,
feste Artefaktklasse, aktiven Publisher und passenden Current-Pointer.

## Konflikt

Wird dieselbe Bootstrap-ID mit anderem Paketnamen, anderer Providerart oder
anderem Zielnamen wiederverwendet, entsteht ausschließlich
`ReleasePublicationBootstrapConflict`.

Die bestehende Entscheidung wird weder angepasst noch ergänzt. Es gibt kein
Upsert und keine teilweise Definitionstoleranz.

## Neutrale Schließung

Eine andere Bootstrap-ID nach bestehender Historie liefert neutral `None`.

`None` bedeutet ausschließlich, dass kein neuer Erstbestand erzeugt wurde.
Es enthält keine Information über vorhandene Publisher, Channels oder
Revisionen.

## Technische Nichtverfügbarkeit

Ungültige Typen, falsche Generatorresultate, fehlende Tabellen,
Transaktionsfehler und inkonsistente Retry-Fakten ergeben detailarm
`ReleasePublicationBootstrapUnavailable`.

Interne IDs, SQL, Tabellen-, DSN-, Host- und ursprüngliche Fehlerdetails
verlassen die Grenze nicht. Fehlerhafte Generatorzüge rollen alle neuen
Fakten zurück.

## Konkurrenz

PostgreSQL sperrt alle Publication-Inventare in fester Reihenfolge mit
`SHARE ROW EXCLUSIVE`.

Zwei konkurrierende unterschiedliche Bootstrap-IDs können daher nicht zwei
Channels oder Publisher erzeugen. Genau eine vollständige Entscheidung
committet; der andere Aufruf sieht danach Historie und bleibt neutral.

SQLite bleibt auf seine serialisierte lokale Transaktion begrenzt.

## Keine Handoff- oder Publishwirkung

Nach erfolgreichem Bootstrap bleiben folgende Tabellen leer:

- `release_publication_handoffs`;
- `release_publication_receipts`;
- `release_publication_reassessments`.

Aktive Publisher-Authority und aktiver Channel allein autorisieren noch
keinen Release. Ein späterer Handoff muss Promotion, aktuelle Release-
Revocation, Publisher-Authority und Channel-Revision erneut prüfen.

## Migration und Bundle-Gate

`20260817_0021` baut linear auf `20260817_0020` auf und ist der einzige Head.

Das LQ-236-Wheelgate erwartet nun 21 lineare Migrationen bis
`20260817_0021`. Entry-Point- und Operatorinventar bleiben unverändert bei
vierzehn beziehungsweise zwölf.

## Nachweis

SQLite-Tests belegen:

- geschlossene typisierte Foundation;
- exakt einen aktiven Erstbestand;
- leere Handoff-/Receipt-/Reassessment-Inventare;
- exakten Retry ohne Generatorzug;
- Konflikt bei abweichender Definition;
- permanente Schließung bei Teilhistorie;
- vollständigen Rollback bei jedem Generatorfehler;
- detailarme technische Nichtverfügbarkeit.

Ein PostgreSQL-16-Konkurrenztest lässt von zwei gleichzeitigen verschiedenen
Bootstrap-IDs genau eine vollständige Control-Plane committen.

Die vollständige Pflichtsuite besteht:

```text
3101 passed, 56 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-250 implementiert keine reguläre Channel- oder Publisher-Lifecycle-
Mutation, Handoff-Entscheidung, Receipt-Aufzeichnung, Reassessment,
Withdrawal, Provider-, CLI-, Git-, Netzwerk-, Publication- oder
Deploymentaktion.

Es werden keine Credentials oder externen Zielressourcen erzeugt.

## Nächster Slice

LQ-251 sollte den autorisierten persistenten Publication-Handoff
implementieren. Er muss Promotion-Evidence und Artefaktbytes erneut aktuell
prüfen, Publisher-Authority und Channel aus dem System of Record auflösen und
idempotent `ready_for_publication` committen, ohne Providerzugriff, Upload oder
Deployment.
