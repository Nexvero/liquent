# LQ-130 — Persistence Boundary for Identity Bindings, Login Transactions, and Browser Sessions

## Status

Architekturentscheidung und Vertrag. Keine Implementierung, keine Datenbank-
technologie, kein Schema, keine Migration, keine Ports/Adapter/Routen und keine
Freigabe einer Laufzeitumgebung. Baut auf LQ-129 (provider-neutrale
Identitätsgrenze) sowie den Session-Verträgen LQ-110/112/113 auf.

## Ziel und Systemgrenze

Diese Entscheidung definiert die **Persistenzgrenze** (System of Record) für genau
drei Datenfamilien und legt **Verantwortlichkeiten, Sicherheitsinvarianten und
Atomaritätsregeln** fest — ohne Technologie-, Schema- oder Adapterwahl:

1. **externe Identitätsbindungen** `(issuer, subject) → UserId`,
2. **Login-Transaktionen** (kurzlebiger OIDC-Ablaufzustand),
3. **Browser-Sessions** (Erzeugung, Rotation, Widerruf).

Außerhalb der Grenze bleiben: Autorisierung und Workspace-Mitgliedschaften
(bestehende interne Grenzen), IdP-Token-Verarbeitung (Callback-Grenze, nicht
persistent) und CSRF-/Cookie-Transport. Zugriff erfolgt später ausschließlich über
explizite Verträge, die hier **nicht** entschieden werden.

## Persistente Verantwortlichkeiten

### Zwingend persistent (System of Record)

- **Interner `UserId`** — stabil, opak, provider-unabhängig.
- **Identitätsbindung** — kanonischer `issuer` und `subject` sowie der zugeordnete
  `UserId` und der Erstellzeitpunkt. Siehe „Admission" und „Issuer-Trust".
- **Login-Transaktion** — `state`, erwarteter `nonce`, PKCE-`code_verifier`, kurze
  Ablaufzeit, „consumed"-Markierung, Erstellzeitpunkt.
- **Browser-Session** — an `UserId` gebundener Record mit Ablauf und Widerrufs-
  zeitpunkt (analog LQ-110/112).
- **Audit-Ereignisse** — minimal, ohne Geheimnisse.

### Admission steuert die Bindungsanlage

Eine **neue** `(issuer, subject)`-Bindung wird **ausschließlich** nach einer
expliziten internen Admission-Entscheidung angelegt: kontrolliertes Onboarding,
eine gültige Einladung oder eine andere vorhandene interne Zulassung. **Eine
erfolgreiche OIDC-Authentifizierung allein erzeugt weder `UserId` noch Binding
noch Berechtigung.** Fehlt eine Admission, endet die Anmeldung neutral, ohne eine
Bindung anzulegen und ohne zu verraten, ob Subject, E-Mail oder Einladung bekannt
sind.

### Niemals gespeichert

- IdP **ID-/Access-/Refresh-Tokens** (nie persistent, nie als `liquent_session`).
- **Passwörter** (existieren nicht).
- **Veränderliche Claims** (E-Mail, Username, Anzeigename) als Identitätsschlüssel;
  höchstens nicht-autoritative Anzeige, nie zur Zuordnung oder Verknüpfung.
- **Rohgeheimnisse in reversibler Form** (Zielrichtung, siehe „CSRF-/Hash-Grenze").

## Sicherheitsinvarianten

### Issuer-Trust wird bei jeder Anmeldung geprüft

Das Identity Binding speichert `issuer` und `subject` kanonisch, aber **keinen
dauerhaft kopierten Trust-Status**. Ob ein Issuer aktuell vertrauenswürdig ist,
wird **bei jeder Anmeldung** gegen die **aktive** Trust-Konfiguration geprüft. Eine
später entzogene Issuer-Freigabe darf durch ein bestehendes Binding **nicht**
umgangen werden: wird der Issuer nicht mehr als vertrauenswürdig geführt, scheitert
die Anmeldung neutral, unabhängig davon, dass eine Bindung existiert.

### CSRF-/Hash-Grenze (bewusst offen gehalten)

Einweg-Hashing für Session-ID, CSRF-Nachweis, `state` und `nonce` — sodass ein
Datenbankabzug keine nutzbaren Credentials liefert — bleibt die **Zielrichtung**.
Ausdrücklich festgehalten:

- Das **bestehende lokale Session-Modell hält derzeit den erwarteten CSRF-Wert
  verfügbar** (Gleichheitsvergleich im Klartext).
- Ein persistenter **Hash-only-Betrieb erfordert später eine angepasste
  Validierungsgrenze** (die vorgelegten Werte hashen und gegen gespeicherte Hashes
  vergleichen).
- Diese **Modell-/Portänderung ist nicht Teil von LQ-130** und darf **nicht
  stillschweigend vorausgesetzt** werden; sie ist eine eigene spätere Entscheidung.

Der PKCE-`code_verifier` muss am Callback wieder verwendbar sein und ist daher kein
Einweg-Hash-Kandidat; er bleibt vertraulich-at-rest, sehr kurzlebig und wird bei
Konsum gelöscht (Krypto-Mechanismus bleibt offen).

### Eindeutigkeit und Konsistenz

- eindeutige Bindung auf `(issuer, subject)`; genau ein `UserId` pro Paar;
  E-Mail-Gleichheit verknüpft nie Konten,
- eindeutige Session-ID; eindeutige Login-`state`,
- referenzielle Konsistenz `Session.UserId → bestehender User` und
  `Binding.UserId → bestehender User`,
- ein Widerruf setzt den Zeitpunkt **monoton einmalig**,
- **Neutralität:** Existenz von Nutzer, Bindung oder Login-Transaktion ist nach
  außen nie unterscheidbar.

### Abgelaufen und widerrufen

Abgelaufene Sessions sowie abgelaufene oder konsumierte Login-Transaktionen sind
**inert** (gelten als abwesend für die Gültigkeit). Widerruf ist **permanent und
idempotent**; ein Restore darf widerrufene oder konsumierte Datensätze **nie**
reaktivieren (siehe „Betrieb").

## Atomaritätsanforderungen

Jede der folgenden Operationen ist **eine** atomare, fail-closed Operation an der
Persistenzgrenze (kein Last-Write-Wins), serialisiert durch die Speicherschicht
(Eindeutigkeit/bedingte Schreibvorgänge), **nicht** durch In-Process-Locks — damit
mehrere App-Instanzen korrekt bleiben:

- **Identitätsbindung anlegen:** nur nach Admission; „finde oder lege genau einmal
  an" ohne Doppelanlage bei Nebenläufigkeit.
- **Login-Transaktion konsumieren:** Claim-Once (genau eine Konsumierung; jede
  Wiederholung findet sie „consumed"/abgelaufen → neutraler Fehlschlag).
- **Session-Erzeugung:** Einfügen nur bei freier ID (sonst neutraler Konflikt).
- **Rotation:** Widerruf des alten und Anlage des neuen Records **gemeinsam**; nie
  beide gleichzeitig aktiv; Principal aus dem bestehenden Record; Ziel-ID-Kollision
  → neutrales Scheitern.
- **Widerruf:** idempotent; erster Widerrufszeitpunkt bleibt.

## Audit- und Betriebsgrenzen

### Minimale Audit-Ereignisse

Append-only, unveränderlich, getrennt von technischen Logs:
`login_started`, `login_verified`, `login_rejected` (nur neutrale Fehlerklasse),
`identity_binding_created`, `session_issued`, `session_rotated`, `session_revoked`,
`logout`. Jedes Ereignis trägt Zeitstempel, Ereignistyp, ggf. internen `UserId` und
eine Correlation-ID — **niemals** Tokens, Session-IDs, CSRF-Werte, PKCE-/`state`/
`nonce`-Werte oder Rohclaims.

### Betrieb

- **Mehrere App-Instanzen:** die Persistenzschicht ist der geteilte System-of-
  Record; Atomarität ausschließlich über den Store; Caches/Queues sind
  rekonstruierbar und nie alleiniger Record.
- **Backup:** verschlüsselte, extern replizierte Backups; regelmäßiger
  Restore-Test.
- **Fail-closed Restore:** Ein Restore aus einem älteren Stand darf **keine**
  möglicherweise später widerrufenen Sessions reaktivieren. Können die
  vollständigen Widerrufs- und Konsumzustände **nicht zweifelsfrei** rekonstruiert
  werden, werden **alle vor dem Restore bestehenden Browser-Sessions und
  Login-Transaktionen global ungültig**; Nutzer müssen sich danach **neu
  authentifizieren**. Im Zweifel gilt ungültig, nie gültig.
- **Aufräumen:** abgelaufene/konsumierte Datensätze sind inert und später
  beschränkt löschbar (Retention), ohne Korrektheit zu berühren.

### Migrations- und Rollback-Grenzen

Daten-/Strukturänderungen sind vorwärts- **und** rückwärtskompatibel
(Expand/Contract, mehrere Releases); Rollback über das zuletzt bekannte Artefakt.
**Verboten** ist jede Migration, die widerrufene Sessions reaktiviert,
Login-Transaktionen „ent-konsumiert" oder Identitätsschlüssel destruktiv
umschlüsselt (nur per eigener Migration-ADR).

### Local/Test-Trennung

- **Unit- und Local-Pfade bleiben beim In-Memory-Adapter** (`InMemoryBrowserSessions`)
  hinter einem expliziten „local only"-Gate.
- Ein **späterer persistenter Adapter benötigt isolierte Integrationstests gegen
  eine wegwerfbare Testinstanz**, getrennt von Unit- und Local-Pfaden.
- **Tests dürfen niemals Shared-, Staging- oder Produktionsdaten verwenden.**
- Persistenter Betrieb bleibt technisch und sichtbar von Local/Test getrennt
  (analog Paper/Live).

## Bewusste Nicht-Ziele

- keine Datenbanktechnologie-Wahl,
- keine Tabellen, Schemata oder Migrationen,
- keine ORM-Modelle, Ports, Adapter oder Routen,
- keine OIDC-Bibliothek oder konkreter Identity Provider,
- keine Änderung des bestehenden CSRF-/Session-Validierungsmodells (Hash-only ist
  eine spätere, eigene Entscheidung),
- kein Composition- oder Production-Wiring, kein Deployment, kein VPS-Zugriff,
- keine CORS-, Autorisierungs- oder Mitgliedschaftsänderung,
- kein föderierter Logout, keine Kontoverknüpfungs-Implementierung,
- kein Release und kein Deployment.

## Nächste Architekturentscheidung

Erst nach dieser Persistenzgrenze dürfen konkrete Ports, Adapter und Routen für
Login-Callback, Identitätsbindung und den persistenten Session Store geplant
werden — jeweils als eigene, kleine Slices mit isolierten Tests.
