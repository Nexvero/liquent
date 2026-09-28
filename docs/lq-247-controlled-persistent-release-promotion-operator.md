# LQ-247 — Controlled Persistent Release Promotion Operator

## Ergebnis

LQ-247 implementiert einen owner-only Offline-Operator für die aktuelle
persistenzgebundene Release-Promotionprüfung.

Der Operator komponiert die LQ-243-System-of-Record-Projektion direkt mit
LQ-244, prüft Bundle und detached SSHSIG read-only und materialisiert
detailarme positive Promotion-Evidence.

Er veröffentlicht und deployt kein Artefakt.

## Prozessgrenze

Der neue Entry Point lautet `liquent-release-promotion`.

Er wird ausschließlich explizit offline gestartet. Es gibt keine HTTP-Route,
keinen App-Startup-Hook, keinen automatischen CI-Schritt und keine Verbindung
zu Package-Repository, Container-Registry oder Deploymentplattform.

Datenbank-Engine und Ressourcen werden nur für den einzelnen Operatorlauf
aufgebaut und anschließend geschlossen.

## Kontrollierte Eingaben

Datenbank-URL, unabhängige Verification-ID und Promotion-Request werden aus
expliziten privaten, regulären und nicht verlinkten Dateien gelesen.

Der Request enthält exakt:

- Pfad zum LQ-236-Bundle;
- Pfad zur detached LQ-237-SSHSIG;
- stabile ausgewählte Key-ID;
- neuen abwesenden Evidence-Zielpfad.

Der Signaturdateiname muss exakt `<bundle-name>.sshsig` sein.

## Keine caller-kontrollierte Authority

Der Request akzeptiert insbesondere keine:

- Registry-Datei oder Registry-Bytes;
- Authority-ID oder Public-Key-Datei;
- Fingerprint-, Policy- oder Statusangabe;
- Rolle, Capability oder Allow-Entscheidung;
- Namespace- oder Algorithmusauswahl;
- behauptete Verification-ID;
- Publish-, Deploy- oder Promotion-Statusmutation.

Unbekannte Requestfelder werden vollständig abgelehnt.

## Unabhängige Verification-Identität

`ReleasePromotionVerifierId` wird aus einer getrennten privaten
Operator-Konfiguration gelesen und beim Aufbau der persistenten Projektion
injiziert.

Die parameterlose Projektion exportiert diese Identität gemeinsam mit dem
aktuellen Trust-Snapshot. Der Request kann sie pro Entscheidung nicht
überschreiben.

Signing-Executor aus LQ-245/246 und Promotion-Verifier bleiben damit
strukturell getrennte Identitäten.

## Genau ein persistenter Trust-Snapshot

Jeder Operatorlauf ruft die persistente Projektion genau einmal auf.

Current-Pointer, Registry-/Policy-Revision, Signer, Key, Status, Fingerprint
und Public Key stammen aus derselben aktuellen Lesesicht. Dieselben
kanonischen Projektionsbytes tragen die Authority-Auflösung und den
`registry_sha256` der Evidence.

Es gibt keinen Registry-Pfad, zweiten Lookup, positiven Cache, Default-Key,
älteren Snapshot oder dateibasierten Fallback.

## Sofortige Revocation-Wirkung

Jede neue Prüfung liest den aktuellen System-of-Record-Stand neu.

Eine committierte Authority-Deaktivierung, Key-Deaktivierung, Expiry,
Revocation oder Policy-Sperre schließt alle später gestarteten Operatorläufe
fail-closed.

Frühere Signing- oder Promotion-Evidence gewährt keine fortdauernde
Authority und wird nicht als Ersatz für die aktuelle Projektion akzeptiert.

## Read-only Bundle- und Signaturprüfung

LQ-244 liest Bundle und Signatur als unveränderliche Snapshots und prüft:

- vollständige LQ-236-Bundle-Struktur und Hashinventare;
- exakte `SHA256SUMS`-Bytes aus demselben Bundle-Snapshot;
- kanonisches SSHSIG-Armor ohne angehängte Bytes;
- Ed25519-Fingerprint gegen den persistenten Public Key;
- Signatur über exakt diese Checksummenbytes;
- festen Namespace `liquent-operations-release-v1`;
- aktive Authority, aktiven Key und aktive Policy.

Der Operator besitzt keinen privaten Key und signiert nichts.

## Kanonische Promotion-Evidence

Positive Evidence ist kompaktes ASCII-JSON mit sortierten Schlüsseln und
genau einem finalen Newline.

Sie bindet Bundle-, Checksum-, Signatur- und Registry-Hash, Source-Commit,
Paket- und Bundle-Version, Signer, Key, Fingerprint, Policy,
Verification-Identität, UTC-Entscheidungszeit sowie die Resultate
`integrity=verified`, `signature=verified`, `authority=current` und
`promotable=true`.

Evidence enthält keine DSN, SQL-, Tabellen-, Host- oder internen Pfaddetails,
keine privaten Keys und keine Registry-Inventare außerhalb der notwendigen
gebundenen öffentlichen Entscheidungsfakten.

## Exklusive Dateimaterialisierung

Das Evidence-Ziel muss abwesend sein. Sein Elternverzeichnis muss existieren
und darf keine Group- oder Other-Rechte besitzen.

Der Operator schreibt zunächst einen eindeutig besessenen temporären Namen
mit `O_EXCL`, Modus `0600`, vollständigen Writes und `fsync`.

Der finale Name entsteht über einen exklusiven Hardlink. Das Verzeichnis wird
anschließend synchronisiert und der temporäre Name entfernt.

Vorhandene Dateien oder Symlinks werden nie geöffnet, gekürzt, ersetzt,
überschrieben oder gelöscht.

## Kein Evidence-Retry als Authority-Ersatz

Eine Promotionprüfung ist eine aktuelle zeitgebundene Entscheidung und kein
idempotenter Signing-Commit.

Ein bereits vorhandener Evidence-Pfad wird deshalb auch bei bytegleichem
Inhalt abgelehnt. Ein neuer Lauf benötigt einen neuen abwesenden Zielpfad und
führt erneut genau eine aktuelle Registry- und Revocationprüfung aus.

Das verhindert, dass alte positive Evidence als vermeintlicher Retry den
aktuellen Trust-Stand umgeht.

## Fehlergrenzen und Exitcodes

Ungültiger privater Input endet mit einem stabilen Inputfehler. Fehlende oder
inaktive aktuelle Authority, ungültiges Bundle oder falsche Signatur ergeben
eine detailarme fachliche Ablehnung.

Projektions-, Datenbank-, OpenSSH-, Clock-, Struktur- oder Dateisystemfehler
bleiben getrennte detailarme technische Nichtverfügbarkeit.

stdout meldet ausschließlich `verified` nach vollständig materialisierter
Evidence. stderr enthält im Fehlerfall nur den stabilen Operatorcode.

Keine ursprüngliche Exception oder interne Infrastrukturangabe verlässt die
Prozessgrenze.

## Bundle-Inventar

`liquent-release-promotion` ist ein neuer installierter Console Entry Point
und ein neues Operatormodul im Runtime-Wheel.

Das LQ-236-Gate erwartet deshalb jetzt vierzehn Entry Points und zwölf
Operatormodule einschließlich Package-Initialisierung.

Bundle-Formatversion, neunzehn Migrationen und Head `20260817_0019` bleiben
unverändert. LQ-247 benötigt keine Migration oder Schemaänderung.

## Nachweis

Tests belegen:

- geschlossenes privates Requestformat ohne Registry- oder Allow-Eingabe;
- genau einen Projektionsaufruf und Hashbindung an dieselben Bytes;
- kanonische positive Evidence;
- echte persistente Bootstrap-, Key-Aktivierungs- und Projektionskomposition;
- echte OpenSSH-Signaturprüfung über einen LQ-236-Kandidaten;
- private exklusive Evidence-Ausgabe ohne Überschreiben;
- fail-closed Symlinks und unsichere Zielverzeichnisse;
- aktualisierte Entry-Point- und Operatorinventare.

Die vollständige Pflichtsuite besteht mit echtem PostgreSQL 16:

```text
3039 passed, 56 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-247 persistiert keine neue Promotion-Decision-Tabelle und mutiert weder
Registry noch Signing-Key. Es gibt keine Veröffentlichung, Package-Version,
Git-Tag-, Commit-, Push-, Registry-, Deployment- oder Rollbackaktion.

Positive Evidence ist nur ein prüfbarer Handoff-Fakt und kein ausgeführter
Release oder Deploymentauftrag.

## Nächster Slice

LQ-248 sollte den kontrollierten Release-Publication-Handoff-Vertrag
entscheiden. Er muss Promotion-Evidence, unveränderliche Artefakthashes,
Zielkanal, Publisher-Authority, Idempotenz, Retention und Reassessment nach
Revocation trennen, ohne bereits Veröffentlichung oder Deployment zu
implementieren.
