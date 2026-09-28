# LQ-223 — Authorized User Lifecycle Mutation

## Ergebnis

LQ-223 implementiert die reguläre persistente User-Lifecycle-Mutation aus
LQ-219 auf den Foundations von LQ-220 bis LQ-222.

Die neue Grenze unterstützt genau:

- Anlage eines neuen aktiven internen Nutzers;
- Deaktivierung eines vollständig entwalteten aktiven Nutzers;
- explizite Reaktivierung eines inaktiven historischen Nutzers.

Jede erfolgreiche Änderung erzeugt eine vollständige neue Nutzerrevision und
eine immutable Change-Entscheidung. Der Slice verändert keine Workspaces und
erteilt keine Membership, Permission oder Management-Authority.

## Getrennte Portoperationen

`AuthorizedUserLifecycleStore` besitzt zwei strukturell getrennte Operationen.

`create_user` akzeptiert Change-ID, `SessionPrincipal` und erwartete aktuelle
Nutzerrevision. Es akzeptiert keine Ziel-UserId.

`change_user_status` akzeptiert zusätzlich einen bestehenden Zielnutzer und
genau `DEACTIVATE` oder `REACTIVATE`. `CREATE` ist an dieser Operation
strukturell unzulässig.

Damit kann ein Caller bei Nutzeranlage weder UserId wählen noch einen
vorhandenen Nutzer als angeblich neu deklarieren.

## SessionPrincipal und aktuelle Authority

Der `SessionPrincipal` identifiziert ausschließlich den Actor.

Für jede neue Change-ID löst die Schreibtransaktion aus dem System of Record
auf:

- Actor existiert und ist aktiv;
- Actor besitzt aktuell aktive User-Lifecycle-Management-Authority;
- erwartete Nutzerrevision ist exakt der Current-Pointer;
- die vollständige Revision entspricht exakt dem operativen Nutzerbestand.

Caller-supplied Rolle, Allow-Boolean, Authority-Snapshot, Statusbehauptung oder
alternativer Actor werden nicht akzeptiert.

Ein committierter Authority- oder Actor-Entzug sperrt jede später neu
begonnene Lifecycle-Entscheidung.

## Nutzeranlage

Bei bestätigter Authority und Current-Revision erzeugt der Adapter intern eine
neue stabile `UserId` über den sicheren Materialgenerator.

Die ID muss ein nichtleerer exakter String sein und wird ohne Normalisierung
als neuer aktiver Nutzer gespeichert. Primärschlüssel und dauerhafte Historie
verhindern Wiederverwendung einer bereits bekannten ID.

Create erzeugt ausdrücklich keine:

- External-Identity-Bindung oder Admission;
- Browser-Session oder Login-Transaktion;
- Workspace-Membership oder Research-Permission;
- Onboarding-, Membership-, Trust- oder Lifecycle-Authority;
- Workspace-Anlage.

Der neue Nutzer ist nur ein aktiver interner Zielkandidat für getrennte spätere
Entscheidungen.

## Vollständiger Drain vor Deaktivierung

Deactivate ist nur für einen bekannten aktuell aktiven Zielnutzer zulässig.

In derselben gesperrten Schreibtransaktion muss für diesen Nutzer vollständig
abwesend sein:

- jede nicht widerrufene und noch nicht abgelaufene Browser-Session;
- jede unverbrauchte und noch nicht abgelaufene Identity-Admission;
- jede aktive gewöhnliche Workspace-Membership;
- jede aktive Onboarding-Management-Authority;
- jede aktive Membership-Management-Authority;
- jede aktive OIDC-Trust-Management-Authority;
- jede aktive User-Lifecycle-Management-Authority;
- jede aktive Workspace-Lifecycle-Management-Authority.

Bereits widerrufene oder abgelaufene Sessions sowie verbrauchte oder
abgelaufene Admissions blockieren nicht.

Unbekannter oder unvollständig lesbarer Bestand wird niemals als erfolgreich
entwaltet behandelt.

## Kein impliziter Cascade

Die User-Lifecycle-Grenze widerruft, löscht oder verändert keine Session,
Admission, Membership, Permission oder Authority.

Jede abhängige Domäne muss vor Deaktivierung über ihre eigene autorisierte
Grenze bereinigt worden sein. Der bestehende letzter-Manager-Schutz bleibt
dadurch wirksam und kann nicht durch Nutzerdeaktivierung umgangen werden.

Schlägt irgendeine Drain-Vorbedingung fehl, bleibt der Nutzer aktiv und es
entstehen weder Revision noch Change-Entscheidung.

## Explizite Reaktivierung

Reactivate ist nur für einen bekannten aktuell inaktiven historischen Nutzer
zulässig.

Erfolg ändert ausschließlich dessen Nutzerstatus auf aktiv. Frühere Sessions,
Admissions, Memberships, Permissions oder Authorities werden nicht erzeugt,
geändert oder reaktiviert.

Der LQ-219-Drain vor jeder zulässigen Deaktivierung stellt sicher, dass alte
aktive abhängige Fähigkeiten bei Reaktivierung nicht stillschweigend wieder
wirksam werden.

## Vollständige Revisionsintegrität

Vor einer Mutation liest der Adapter den vollständigen Member-Satz der
erwarteten Current-Revision und den vollständigen operativen Nutzerbestand in
stabiler ID-Reihenfolge.

Beide müssen exakt übereinstimmen. Fehlende, zusätzliche, doppeldeutige oder
statusabweichende Fakten sind technische Inkonsistenz und werden nicht durch
eine neue Revision überdeckt.

Erfolg erzeugt eine intern generierte neue `UserLifecycleRevisionId` und
speichert darin jeden historischen Nutzer mit seinem resultierenden Status.

Operativer Nutzerstatus, vollständige neue Revision, atomarer Current-Pointer
und immutable Change-Entscheidung committen gemeinsam oder gar nicht.

## Erwartete Revision und Konkurrenz

Jede Operation verlangt die exakte erwartete Current-Revision. Es gibt keinen
revisionslosen regulären Start, Last-write-wins oder blindes Upsert.

PostgreSQL sperrt Identity-, Authority-, Revisions-, Change- und sämtliche
Drain-relevanten Tabellen in einer kurzen Transaktion. Es findet darin kein
Datei-, Netzwerk-, Provider- oder anderes externes I/O statt.

Konkurrierende Creates gegen dieselbe erwartete Revision werden geordnet.
Genau einer kann eine neue Revision committen; der andere sieht anschließend
eine stale Revision und wird neutral abgelehnt.

Die feste Lock-Reihenfolge und geordnete Snapshot-Verarbeitung folgen der
PostgreSQL-Gegenprüfung für kurze Transaktionen und Deadlock-Vermeidung.

## Idempotenz und Konflikt

Jede Operation besitzt eine stabile `UserLifecycleChangeId`.

Eine exakte Wiederholung mit identischem Actor, Intent, erwarteter Revision und
bei Statusänderung identischem Ziel liefert das bereits committete Ergebnis.

Bei Create wird dabei dieselbe intern erzeugte Ziel-UserId zurückgegeben; der
Generator wird nicht erneut verwendet.

Der Retry wird vor aktueller Authority aufgelöst und bleibt deshalb nach
späterem Actor- oder Authority-Entzug verfügbar.

Wiederverwendung derselben Change-ID mit anderem Actor, Intent, Ziel oder
erwarteter Revision ist ein detailfreier Konflikt.

## Persistenz und Indizes

Die bereits mit LQ-220 angelegten Nutzerrevision-, Member-, Current- und
Change-Tabellen tragen die Mutation. Es entsteht keine zweite Statusquelle.

Revision `20260813_0016` ergänzt ausschließlich die zwei zuvor fehlenden
Drain-Indizes:

- Browser-Sessions nach `user_id`;
- Identity-Admissions nach `target_user_id`.

Membership- und Onboarding-Drain benötigen keinen redundanten Zusatzindex,
weil ihre Primärschlüssel bereits mit `user_id` beginnen. Das wurde in der
PostgreSQL-Best-Practices-Gegenprüfung ausdrücklich berücksichtigt.

Die Migration erzeugt keinen Nutzer, Status, Authority, Pointer oder Change.

## Ablehnung und technische Fehler

Inaktiver oder unbekannter Actor, fehlende Authority, stale Revision,
unbekanntes Ziel, falscher Zielstatus oder nicht vollständiger Drain ergeben
dieselbe neutrale Ablehnung ohne Bestandsdetails.

Abweichende Change-ID-Wiederverwendung ist ein eigener detailfreier Konflikt.

Ungültige Generatorwerte, beschädigte Revisionen, inkonsistenter operativer
Bestand, Datenbank-, Encoding-, Struktur-, Transaktions- oder Commitfehler
enden als detailfreie technische Nichtverfügbarkeit.

Keine Antwort oder Exception enthält Actor, Ziel, Status, Authority, Revision,
Change-ID, Session, Admission, SQL, Tabelle, Constraint, Host, Port oder DSN.

## Nachweise

Die SQLite-Tests belegen:

- Create mit ausschließlich intern erzeugter UserId;
- Deactivate und Reactivate mit vollständigen neuen Revisionen;
- unveränderte Historie und aktuelle operative Status;
- separate Ablehnung jeder einzelnen Drain-Abhängigkeit;
- keine Statusänderung bei abgelehntem Drain;
- stale Revision und inaktiven Actor fail-closed;
- exakten Create-Retry mit identischem internem Ziel nach Authority-Entzug;
- Konflikt bei abweichender Wiederverwendung;
- Vorhandensein der zwei gezielten Drain-Indizes.

Der PostgreSQL-Test führt zwei echte gleichzeitige Creates gegen dieselbe
Revision aus und belegt genau einen Erfolg ohne technische Ausnahme.

Die persistente Session-Grenze liest Sessions nun nur für aktuell aktive
Nutzer und verlangt bei Anlage oder Rotation einen aktiven, auf PostgreSQL
gesperrten Nutzer. Dadurch kann nach dem Drain weder eine alte Session weiter
auflösen noch konkurrierend eine neue Session für den deaktivierten Nutzer
entstehen.

## Bewusst nicht enthalten

- keine Workspace-Anlage oder -Deaktivierung;
- keine automatische Bereinigung abhängiger Domänen;
- keine reguläre Authority-Mutation oder Recovery;
- keine Self-Sign-up-, Invitation- oder OIDC-Autoprovisionierung;
- keine CLI, Request-/Resultatdatei oder Runbook;
- keine HTTP-Route, Settings-, Startup- oder Runtime-Verdrahtung;
- keine physische Nutzerlöschung oder ID-Wiederverwendung.

## Nächster Schritt

LQ-224 sollte die reguläre Workspace-Lifecycle-Mutation implementieren:
Create mit intern erzeugter stabiler WorkspaceId und atomar gebundenem ersten
Onboarding-Manager sowie terminales Deactivate gegen die vollständige aktuelle
Workspace-Revision.

Danach können getrennte kontrollierte Offline-Operatoren für User- und
Workspace-Lifecycle folgen.
