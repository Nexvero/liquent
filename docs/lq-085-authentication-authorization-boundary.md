# LQ-085 — Authentication and Authorization Boundary

## Status

- Die minimale Identitäts-, Session- und Berechtigungsgrenze für Slice 1 ist
  verbindlich definiert.
- Shared Environments bleiben bis zur Implementierung dieses Vertrags für den
  Research-Start gesperrt.
- Noch keine Provider-, Passwort-, SSO-, Token- oder Datenbankimplementierung.

## Product Outcome

Ein angemeldeter Nutzer darf ausschließlich Research-Ressourcen eines
Workspaces lesen oder verändern, in dem er eine aktive Mitgliedschaft besitzt.
Authentifizierung beantwortet „Wer ist der Nutzer?“. Autorisierung beantwortet
für jede Ressource separat „Darf dieser Nutzer diese Aktion ausführen?“.

## Minimale Objekte

| Objekt | Zweck | Slice-1-Regel |
|---|---|---|
| User | stabile menschliche Identität | kein Broker- oder Portfolioinhaber |
| Session | zeitlich begrenzter Browserzugriff | widerrufbar, serverseitig prüfbar |
| Workspace Membership | Beziehung User ↔ Workspace | einzige Mandantengrenze in Slice 1 |
| Permission | erlaubte Research-Aktion | klein und explizit, keine freie Rollenmatrix |

Service Accounts, persönliche API-Tokens und Enterprise-Identitätsprovider sind
nicht Teil dieses Slices.

## Berechtigungen

Slice 1 besitzt genau zwei fachliche Rechte:

- `research:read` — Jobstatus und Evidence im zugehörigen Workspace lesen.
- `research:write` — validierten Research-Job im zugehörigen Workspace starten.

Eine aktive Workspace-Mitgliedschaft ist immer erforderlich. `research:write`
impliziert für diesen Slice `research:read`. Systemweite Administratorrechte
werden nicht als Abkürzung durch die Produkt-API geführt.

## Ressourcenzuordnung

Jeder Experiment-Snapshot und jeder Job muss vor Freigabe für Shared
Environments eindeutig eine `workspace_id` tragen. Autorisierung erfolgt gegen
die Workspace-ID der gespeicherten Ressource, niemals gegen eine vom Client nur
behauptete Workspace-Zugehörigkeit.

```text
Session → User → aktive Membership → Workspace
                                      ↓
                              Experiment → Job → Evidence
```

Fehlt diese eindeutige Zuordnung, scheitert die Aktion fail-closed.

## Browser-Session

Für die Weboberfläche gilt später:

- Session-Identifier ausschließlich in einem `Secure`, `HttpOnly`-Cookie,
- `SameSite=Lax` als Mindestgrenze,
- feste absolute und inaktive Ablaufzeit,
- Rotation nach erfolgreicher Anmeldung und Rechteänderung,
- serverseitiger Widerruf bei Logout oder Sicherheitsereignis,
- mutierende Requests benötigen zusätzlich einen CSRF-Nachweis.

Tokens werden nicht in Local Storage, URL-Parametern oder Client-Logs abgelegt.
Konkrete Laufzeiten und der Authentifizierungsprovider werden erst im
Implementierungsslice festgelegt.

## API-Verhalten

| Situation | HTTP | Öffentlicher Code |
|---|---:|---|
| keine oder ungültige Session | 401 | `authentication_required` |
| Session gültig, Recht fehlt | 403 | `permission_denied` |
| Workspace-Ressource nicht sichtbar | 404 | bestehender neutraler Not-found-Code |
| CSRF-Nachweis fehlt/ungültig | 403 | `csrf_validation_failed` |

Eine 403-Antwort verrät nicht, ob eine fremde Job- oder Workspace-ID existiert.
Für fremde Ressourcen wird 404 verwendet, um Ressourcenermittlung zu vermeiden.

## Lokale Entwicklung und CI

Der aktuelle `local`-/`ci`-Research-Pfad bleibt ein ausdrücklich konfigurierter
Entwicklungsmodus. Er ist keine Authentifizierungsumgehung für Preview oder
Produktion. LQ-084 bleibt unverändert aktiv, bis Sessionprüfung,
Workspace-Zuordnung und Rechteprüfung vollständig Ende-zu-Ende nachgewiesen sind.

## Audit-Grenze

Später auditierbar sind Anmeldung, Logout, Session-Widerruf, verweigerter Zugriff
und erfolgreicher Research-Start. Nicht geloggt werden Session-Identifier,
CSRF-Werte, Passwörter, vollständige Request-Bodies oder lokale Dateipfade.

## Bewusst nicht entschieden oder gebaut

- kein eigener Passwortspeicher und keine Passwort-Reset-Flows,
- keine Auswahl zwischen OAuth, Passkeys, Magic Link oder Enterprise SSO,
- keine JWT- oder API-Key-Festlegung,
- kein Rollen-Editor, Einladungsflow oder Organisationshierarchie,
- keine Datenbanktabellen, Middleware oder Login-Oberfläche,
- keine Freischaltung für Preview/Produktion,
- kein Release oder Deployment.

## Akzeptanzkriterien

1. Jede Shared-Environment-Anfrage besitzt eine verifizierte User-Identität.
2. Jede Research-Ressource ist serverseitig einem Workspace zugeordnet.
3. Lesen erfordert aktive Membership und `research:read`.
4. Starten erfordert aktive Membership, `research:write` und gültigen CSRF-Nachweis.
5. Fremde Ressourcen werden nicht durch 403 oder unterschiedliche Details verraten.
6. Sessions sind Cookie-basiert, widerrufbar und zeitlich begrenzt.
7. Geheimnisse und Sessionwerte erscheinen nicht in Logs oder URLs.
8. LQ-084 bleibt bis zum vollständigen Ende-zu-Ende-Nachweis bestehen.

## Nächster Schritt

LQ-086 definiert ausschließlich stabile `UserId`, Membership-Status und die
beiden Permission-Werte als kleine Domänentypen. Session-Speicherung,
Middleware und Provider folgen erst danach in getrennten Slices.
