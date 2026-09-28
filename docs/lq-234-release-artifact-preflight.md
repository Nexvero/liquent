# LQ-234 — Release Artifact Preflight

## 1. Ergebnis

LQ-234 baut und prüft erstmals die tatsächlichen Python-Release-Artefakte des
kumulierten LQ-177-Stands.

Wheel und Source-Distribution lassen sich erfolgreich aus dem aktuellen
Worktree erzeugen. Das Wheel enthält Runtime-Code, alle Migrationen, alle
Operatormodule und sämtliche zwölf Console Entry Points; eine separate
temporäre Wheel-Installation ist vollständig importierbar.

Der Preflight findet jedoch eine operative Packaging-Lücke: Die
Source-Distribution enthält weder `operations/` noch `docs/`. Damit ist sie
allein kein vollständiges Handoff-Bundle für die owner-only Control Plane.

LQ-234 veröffentlicht kein Artefakt und ändert keine Packaging-Konfiguration.

## 2. Auditgrenze

Geprüft wurden:

- isolierter Wheel- und sdist-Build;
- Distribution-Metadaten und Version;
- Console Entry Points;
- Operatormodule;
- Alembic-Migrationen;
- separate temporäre Wheel-Installation;
- Importierbarkeit aller Entry Points;
- Python-Bytecode-Kompilierung der Installation;
- Inhalt der Source-Distribution;
- lokale Build-Artefaktbereinigung.

Tests und PostgreSQL-Verifikation aus LQ-231 bleiben unverändert maßgeblich.

## 3. Build-Laufzeit

Der Build verwendete die vorhandene Projektlaufzeit aus dem Schwester-
Worktree:

- Python 3.12;
- `build` 1.5.0;
- `wheel` 0.47.0;
- aktuelles Setuptools aus derselben verifizierten `.venv`.

Der aktuelle LQ-183-Quellbaum blieb die einzige Buildquelle.

## 4. Isolierter Buildpfad

Artefakte wurden ausschließlich in einem eindeutigen temporären Verzeichnis
unter `/tmp` ausgegeben.

Der Build lief mit `--no-isolation`, damit keine Netzwerkauflösung oder
unkontrollierte Installation neuer Buildabhängigkeiten erforderlich war.

Es wurde kein Repository-`dist/` erzeugt und kein Paketindex angesprochen.

## 5. Erzeugte Artefakte

Der Build erzeugte erfolgreich:

```text
liquent-0.0.1-py3-none-any.whl
liquent-0.0.1.tar.gz
```

Die Paketversion ist weiterhin `0.0.1`.

Der Preflight entscheidet keine neue Version und nimmt keinen Release-Tag vor.

## 6. Wheel-Inhalt

Das Wheel enthält die beiden Python-Paketräume:

- `liquent`;
- `liquent_platform`.

Die neuen Identity-, Persistence-, Operator-, Runtime- und
Application-Module sind enthalten.

Tests, Dokumentation und Operationsdateien sind erwartungsgemäß nicht Teil des
Runtime-Wheels.

## 7. Migrationen im Wheel

Der Wheel-Scan findet genau 16 Python-Migrationsdateien.

Enthalten sind der Baseline-Start, Identity/Admission, alle neuen Foundation-
und Managementmigrationen sowie der aktuelle Head:

```text
20260813_0016_user_lifecycle_indexes.py
```

Damit kann eine Wheel-Installation den vollständigen linearen Alembic-Pfad
programmatisch laden.

## 8. Operatormodule im Wheel

Der Wheel-Scan findet zehn Module unter `liquent_platform/operators`,
einschließlich `__init__.py`.

Enthalten sind die produktiven Grenzen für:

- initialen Bootstrap;
- OIDC-Trust-Management;
- Membership-Management;
- Trust- und Membership-Authority-Lifecycle;
- beide Recovery-Domänen;
- User- und Workspace-Lifecycle.

## 9. Console Entry Points

Die Wheel-Metadaten enthalten exakt zwölf Console Scripts:

- `liquent-control-plane`;
- `liquent-health-check`;
- `liquent-migrate`;
- `liquent-initial-bootstrap`;
- `liquent-oidc-trust`;
- `liquent-membership-management`;
- `liquent-oidc-trust-authority`;
- `liquent-membership-authority`;
- `liquent-oidc-trust-authority-recovery`;
- `liquent-membership-authority-recovery`;
- `liquent-user-lifecycle`;
- `liquent-workspace-lifecycle`.

Kein erwarteter Entry Point fehlt und kein unbekannter wurde ergänzt.

## 10. Separate Wheel-Installation

Das Wheel wurde mit `--no-deps` in ein neues temporäres Target installiert.

Die Laufzeitabhängigkeiten kamen weiterhin aus der bereits LQ-231-verifizierten
Projekt-`.venv`; der importierte `liquent`-Distributionpfad kam aus dem neuen
Target.

Alle zwölf Console-Entry-Point-Objekte konnten über
`importlib.metadata.EntryPoint.load()` geladen werden.

## 11. Installationskompilierung

Der gesamte temporär installierte Wheel-Inhalt bestand `compileall`.

Damit sind keine Syntax-, Encoding- oder fehlenden Moduldateifehler im
gebauten Runtime-Artefakt sichtbar.

Dieser Nachweis ergänzt die Quellbaumtests, ersetzt sie aber nicht.

## 12. Artefakt-Hashes

Der erste vollständige Build erzeugte folgende Build-spezifischen SHA-256-
Werte:

```text
fbeab156122648a98f8a1adef085498e0f92f8f23b46ece2220437a064e217fc  wheel
def5f10161a398ac16f0d5492b86312c2946c52a5322dc86ee52dcc8eb09c239  sdist
```

Die Artefakte wurden nach dem Audit entfernt und nicht veröffentlicht.

Die Werte sind Evidenz dieses Laufs, keine signierte Release-Provenance.

## 13. Source-Distribution-Inhalt

Die Source-Distribution enthält den Python-Quellbaum, Buildmetadaten, README
und 217 Testdateien.

Eine explizite Inhaltszählung bestätigt zugleich:

```text
operations=0
docs=0
tests=217
```

Die neuen neun Operations-Runbooks und die Slice-/Auditdokumentation fehlen.

## 14. Warum das operativ relevant ist

Die owner-only Operatoren sind absichtlich keine selbsterklärende öffentliche
API.

Sichere Bedienung hängt an den dokumentierten Regeln für:

- private DSN- und Requestdateien;
- stabile Change- und Recovery-IDs;
- exakte Retry-Grenzen;
- erwartete Revisionen;
- detailfreie Ausgänge;
- sichere Resultatbewahrung und Cleanup;
- getrennten Bootstrap, Lifecycle und Recovery.

Ein Release-Handoff nur aus Wheel plus aktuellem sdist würde diese
Betriebsanleitungen nicht transportieren.

## 15. Wheel versus operatives Bundle

Das Runtime-Wheel ist technisch vollständig und soll nicht automatisch alle
Repository-Dokumente enthalten.

Die Lücke liegt deshalb nicht zwingend im Wheel. Offen ist die Entscheidung,
welches Artefakt den operatorischen Handoff bildet:

- erweiterte Source-Distribution;
- separates versioniertes Operationsbundle;
- oder ein Release-Manifest, das Wheel, Runbooks und ausgewählte Verträge
  gemeinsam bindet.

LQ-234 entscheidet diese Packaging-Policy noch nicht.

## 16. Reproduzierbarkeit

Ein zweiter reiner sdist-Build erzeugte einen anderen SHA-256-Wert als der
erste vollständige Build.

Das ist bei standardmäßig zeitstempelabhängigen Python-Archiven erwartbar,
zeigt aber, dass derzeit kein reproducible-build-Claim belegt ist.

Reproduzierbarkeit, Signierung, SBOM und Provenance bleiben separate
Release-Supply-Chain-Themen und dürfen nicht aus diesem Preflight abgeleitet
werden.

## 17. Lokale Bereinigung

Der Build erzeugte temporär:

- Repository-`build/`;
- `src/liquent.egg-info/`;
- zwei eindeutig benannte `/tmp`-Verzeichnisse.

Alle vier Buildbereiche wurden nach Inhaltsprüfung entfernt. Sie waren
ausschließlich von LQ-234 erzeugt und nicht wiederherstellbar erforderlich.

Git-Scope und ignored-Artefaktbestand enthalten daraus keinen neuen Eintrag.

## 18. Release-Handoff-Entscheidung

Der Python-Runtime-Artefaktpfad ist technisch grün.

Der vollständige operative Release-Handoff bleibt jedoch blockiert, solange
kein versioniertes Artefakt die Runbooks und die notwendige Release-Evidenz mit
dem gebauten Wheel verbindet.

Dieser Blocker betrifft Packaging und Übergabe, nicht LQ-177-Produktlogik oder
PostgreSQL-Readiness.

## 19. Nicht ausgeführte Aktionen

LQ-234 hat keine:

- Packaging-Konfigurationsänderung;
- Versionserhöhung oder Tag-Erzeugung;
- Artefaktveröffentlichung oder Registry-Aktion;
- Signierung, SBOM- oder Provenance-Erzeugung;
- Branch-, Staging-, Commit-, Push- oder PR-Aktion;
- Deployment- oder Environment-Mutation.

## 20. Nächster Slice

LQ-235 soll den Vertrag für ein kontrolliertes operatives Release-Bundle
entscheiden.

Er muss festlegen, welche Runbooks, Verträge, Checksummen, Testevidenz,
Versionsbindung und Manifestfelder gemeinsam mit dem Wheel übergeben werden,
ohne Secrets, private Resultate oder environmentbezogene Credentials
einzuschließen.

## 21. Bundle-Vertrag durch LQ-235

LQ-235 entscheidet ein separates deterministisches Operationsbundle aus genau
einem Wheel, neun freigegebenen Runbooks, ausgewählten Sicherheitsverträgen,
kanonischem Manifest, Checksummen und strukturierten Verifikationsergebnissen.

Dirty Source ist unzulässig. Ein unsigned Archiv bleibt Kandidat; Promotion
verlangt eine detached Signatur über `SHA256SUMS` und unabhängige Prüfung.
Die unvollständige sdist ist kein Bestandteil der Formatversion 1.
