# LQ-233 — Commit and Pull Request Scope Plan

## 1. Ergebnis

LQ-233 entwirft den sicheren Git- und Review-Zuschnitt für den kumulierten
LQ-184-bis-LQ-232-Arbeitsbaum.

Empfohlen wird ein benannter Branch vom aktuellen detached HEAD und genau ein
atomarer kumulierter Implementierungscommit für den gesamten uncommitted
Scope.

Die fachliche Reviewbarkeit wird nicht über künstliche Zwischencommits,
sondern über klar getrennte PR-Reviewabschnitte, Migrationsgruppen,
Testnachweise und Runbooks hergestellt.

LQ-233 führt weder Branch-Erzeugung, Staging, Commit, Push noch Pull Request
aus.

## 2. Ausgangsbasis

Der aktuelle detached HEAD ist `83699b1`.

Er enthält vier zusammenhängende Commits vor `origin/main`:

```text
b5d426e feat: persist identity bindings and consume admissions atomically
530f5dc feat: provision persistent identity admissions exactly once
3e83188 docs: decide where an authorized onboarding decision comes from
83699b1 docs: define persistent identity authority foundations
```

Diese Commits sind fachliche Vorgänger aus den Pull Requests #118 bis #121 und
gehören zur Basis der neuen Arbeit.

## 3. Aktueller uncommitted Scope

Nach LQ-232 umfasst der Worktree:

- 21 veränderte getrackte Dateien;
- 187 neue ungetrackte Dateien;
- insgesamt 208 uncommitted Dateien;
- null gestagte Dateien.

Nach Top-Level-Bereich sind betroffen:

- 51 Dokumentationsdateien;
- 10 Operationsdateien;
- 69 Dateien unter `src`;
- 77 Testdateien;
- `pyproject.toml`.

Die Zahlen schließen ignorierte Caches aus.

## 4. Warum ein chronologischer Slice-Commit pro LQ nicht sicher ist

Die Slices wurden im selben Worktree iterativ aufeinander aufgebaut.

Zentrale Dateien enthalten Änderungen aus vielen späteren Slices zugleich:

- `identity/ports.py`;
- `persistence/identity_errors.py`;
- `transport/http/app.py`;
- `configuration.py`;
- `operators/initial_bootstrap.py`;
- `docs/technical-status-and-roadmap.md`;
- `pyproject.toml`.

Eine Datei lässt sich deshalb nicht allein nach ihrem letzten Slice zuordnen.

## 5. Unsichere historische Zwischenstände

Der finale Identity-Bootstrap erwartet inzwischen User- und Workspace-
Lifecycle-Revisionstabellen aus den Migrationen 0014 bis 0016.

Würde sein aktueller Code in einem frühen Identity-Commit landen, während die
späteren Migrationen noch fehlen, wäre `upgrade_to_head` formal erfolgreich,
der Bootstrap aber gegen fehlende Tabellen nicht lauffähig.

Umgekehrt könnten spätere Migrationen ohne die zugehörigen finalen Adapter und
Modelle unreviewbare Zwischenzustände erzeugen.

Ein sauberer chronologischer Split erforderte die Rekonstruktion historischer
Dateiversionen und vollständige Tests jedes Zwischenstands. Das ist keine
mechanische Staging-Aufgabe.

## 6. Risiko von Hunk-Staging

Interaktives Hunk-Staging in den großen gemeinsam bearbeiteten Dateien könnte:

- Ports ohne Implementierung veröffentlichen;
- Exceptions ohne Verbraucher abtrennen;
- Runtime-Wiring vor Persistenz einführen;
- Operator-Entry-Points ohne Module committen;
- Roadmap und Tests vom tatsächlichen Codezustand entkoppeln;
- eine nicht lineare oder nicht ausführbare Migrationsfolge erzeugen.

LQ-233 empfiehlt deshalb kein `git add -p` für eine künstliche Slice-Historie.

## 7. Empfohlener Branch

Bei späterer ausdrücklicher Autorisierung sollte zuerst ein Branch direkt vom
aktuellen detached HEAD erzeugt werden.

Empfohlener Name:

```text
codex/lq-177-shared-environment-readiness
```

Der Branchname beschreibt das erreichte Gesamtergebnis und verwendet den
vorgegebenen `codex/`-Prefix.

Branch-Erzeugung darf nicht stillschweigend mit Staging oder Commit gekoppelt
werden.

## 8. Empfohlener einzelner Commit

Empfohlener Commit-Titel:

```text
feat: complete persistent shared-environment control plane
```

Der Commit sollte alle 208 uncommitted Dateien enthalten, nachdem der staged
Scope erneut gegen LQ-232 geprüft wurde.

Der Commit ist groß, aber atomar ausführbar und entspricht exakt dem gemeinsam
mit 2887 Tests verifizierten Zustand.

## 9. Commit-Body

Der Commit-Body sollte knapp folgende Fähigkeiten nennen:

- persistente Identity-, Admission-, Login- und Sessiongrundlagen;
- aktuelle OIDC-Konfiguration und Production-Composition;
- persistente Membership- und Research-Autorisierung;
- revisionsgebundene Trust- und Membership-Mutation;
- Authority-Lifecycle, Lockout-Schutz und Recovery;
- regulären User- und Workspace-Lifecycle;
- owner-only Offline-Operatoren und Runbooks;
- integrierte PostgreSQL- und Runtime-Nachweise.

Er sollte außerdem `2887 passed`, davon `74 PostgreSQL-Integrationen`, nennen.

## 10. Empfohlener PR-Titel

```text
Complete persistent shared-environment identity and control plane
```

Der Titel ist breiter als ein einzelner Lifecycle-Slice und bildet den
tatsächlichen kumulierten Umfang ab.

Ein enger Titel nur zu LQ-229 oder LQ-231 würde Reviewer über den Scope
irreführen.

## 11. PR-Reviewabschnitt A — Identity und Onboarding

Reviewer beginnen mit:

- Migrationen 0003 und 0004;
- persistenten User-/Workspace- und External-Identity-Fakten;
- initialem Bootstrap;
- autorisierter Onboarding-Entscheidung;
- Admission-Provisionierung;
- interner Composition.

Zentrale Dokumente sind LQ-184 bis LQ-188.

## 12. PR-Reviewabschnitt B — Login, Sessions und Runtime

Danach folgen:

- Migrationen 0005 bis 0007;
- Login-Transaktionen;
- persistente Browser-Sessions;
- aktive OIDC-Client-Konfiguration;
- Verifier-Composition;
- Process-Konfiguration und HTTP-Client-Ownership;
- kontrolliertes App-/Entrypoint-Wiring.

Zentrale Dokumente sind LQ-189 bis LQ-194 und LQ-197.

## 13. PR-Reviewabschnitt C — Research-Membership

Dieser Abschnitt umfasst:

- Migration 0008;
- aktuelle Membership- und Permission-Auflösung;
- fail-closed Research-Wiring;
- aktuelle Revocation-Wirkung in derselben App-Instanz.

Zentrale Dokumente sind LQ-195 und LQ-196.

## 14. PR-Reviewabschnitt D — Trust-Control-Plane

Dieser Abschnitt umfasst:

- Migrationen 0009 bis 0011;
- OIDC-Trust-Authority und Bootstrap;
- revisionsgebundene Login-Bindung;
- autorisierte Trust-Aktivierung, Rotation und Deaktivierung;
- Offline-Operator und initiales Bootstrap-Runbook.

Zentrale Dokumente sind LQ-198 bis LQ-205.

## 15. PR-Reviewabschnitt E — Membership-Control-Plane

Dieser Abschnitt umfasst:

- Migration 0012;
- workspacebezogene Management-Authority;
- vollständige Membership-Revisionen;
- autorisierte Membership-/Permission-Mutation;
- Bootstrap und owner-only Operator.

Zentrale Dokumente sind LQ-206 bis LQ-210.

## 16. PR-Reviewabschnitt F — Authority-Lifecycle und Recovery

Dieser Abschnitt umfasst:

- Migration 0013;
- vollständige Authority-Set-Revisionen;
- Anchor, Grant, Deactivate und Reactivate;
- letzter-Manager-Schutz;
- eng begrenzte Offline-Recovery;
- getrennte Lifecycle- und Recovery-Operatoren.

Zentrale Dokumente sind LQ-211 bis LQ-218.

## 17. PR-Reviewabschnitt G — User-/Workspace-Lifecycle

Der letzte fachliche Abschnitt umfasst:

- Migrationen 0014 bis 0016;
- vollständige User- und Workspace-Revisionen;
- Bootstrap-Revision-Observability;
- reguläre Create-/Deactivate-/Reactivate-Grenzen;
- Drain und terminale Workspace-Deaktivierung;
- owner-only Lifecycle-Operatoren.

Zentrale Dokumente sind LQ-219 bis LQ-229.

## 18. PR-Reviewabschnitt H — End-to-End und Handoff

Zum Abschluss prüfen Reviewer:

- LQ-230-PostgreSQL-End-to-End-Kette;
- LQ-231-Verifikationsprotokoll;
- LQ-232-Handoff-Audit;
- alle Operations-Runbooks;
- aktualisierten Roadmap-Kopf;
- fehlende Runtime-Imports der Offline-Control-Plane.

Dieser Abschnitt bestätigt den Gesamtclaim, führt aber keine neue Funktion ein.

## 19. Staging-Plan bei späterer Autorisierung

Der sichere Ablauf ist:

1. Branch vom exakten aktuellen HEAD erzeugen;
2. `git status --short` erneut sichern;
3. nur die bekannten Top-Level-Ziele `docs`, `operations`, `src`, `tests` und
   `pyproject.toml` stagen;
4. keine ignorierten Dateien mit Force hinzufügen;
5. staged Dateizahl und Top-Level-Verteilung gegen LQ-232/LQ-233 vergleichen;
6. `git diff --cached --check` ausführen;
7. staged Secret-Scan ausführen;
8. staged Diff nach den acht Reviewabschnitten prüfen;
9. erst danach committen.

LQ-233 führt keinen dieser Schritte aus.

## 20. Testplan vor Commit und PR

Vor Commit sollte mindestens erneut laufen:

- vollständige normale Suite;
- verpflichtende PostgreSQL-Suite mit echtem DSN;
- `git diff --cached --check`;
- Konfliktmarkersuche;
- Migration-Head-Prüfung;
- Entry-Point-Importprüfung.

Nach Push muss CI denselben PostgreSQL-Pflichtpfad ausführen. Ein lokaler grüner
Lauf ersetzt das Remote-Release-Gate nicht.

## 21. Alternative: mehrere Commits

Mehrere Commits sind nur vertretbar, wenn ausdrücklich zusätzliche Zeit für
historische Rekonstruktion und Tests jedes Zwischenstands eingeplant wird.

Eine mögliche Zielarchitektur wären die Reviewabschnitte A–G als Commits plus
Handoff-Dokumentation. Sie kann aber nicht durch bloße Dateigruppierung aus dem
aktuellen Endstand gewonnen werden.

Ohne diese Rekonstruktion ist ein einzelner grüner atomarer Commit sicherer als
eine scheinbar saubere, tatsächlich nicht ausführbare Zwischenhistorie.

## 22. Nicht ausgeführte Aktionen

LQ-233 hat keine:

- Branch-Erzeugung;
- Staging-Aktion;
- Commit-Erzeugung oder Amend;
- Rebase-, Cherry-pick- oder History-Rewrite-Aktion;
- Push- oder Pull-Request-Erzeugung;
- GitHub-, CI- oder Deployment-Mutation;
- Änderung an Produktcode, Migrationen oder Tests.

## 23. Nächster Schritt

Der nächste Schritt benötigt eine explizite Benutzerentscheidung zwischen:

- Umsetzung des empfohlenen atomaren Branch-/Commit-/PR-Pfads; oder
- aufwendiger historischer Rekonstruktion mehrerer jeweils vollständig grüner
  Commits.

Ohne diese Autorisierung bleibt der technisch verifizierte Worktree bewusst
unpubliziert.

## 24. Artefakt-Preflight durch LQ-234

LQ-234 bestätigt, dass Wheel und Source-Distribution gebaut werden können und
das Wheel alle Migrationen, Operatormodule und zwölf Entry Points enthält.

Die Source-Distribution enthält jedoch weder `operations/` noch `docs/`.
Damit bleibt vor einem operativen Release zusätzlich zu Branch/Commit/PR eine
explizite Bundle-Entscheidung für Runbooks und Release-Evidenz erforderlich.
