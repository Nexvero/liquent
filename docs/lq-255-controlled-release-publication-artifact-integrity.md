# LQ-255 — Controlled Release Publication Artifact Integrity

## Ergebnis

LQ-255 implementiert die kontrollierte lokale Artifact Source und den
bytegenauen Integritätscheck für einen bereits vorbereiteten Publication-
Attempt.

Der Slice liest Bundle, detached Signatur und historische Promotion-Evidence,
prüft sie vollständig und erzeugt ein read-only verifiziertes Payload. Er
kontaktiert keinen Publication-Provider und führt keinen Upload aus.

## Öffentliche Prüfgrenze

`ReleasePublicationArtifactIntegrityCheck.verify_artifacts` akzeptiert nur:

- eine bestehende Execution-ID;
- eine bestehende Attempt-ID.

Der Aufrufer liefert keinen Handoff, Pfad, Dateinamen, Hash, Key, Publisher,
Channel, Provider, Zielnamen oder Allow-Wert.

Alle Bindungen werden aus der vorbereiteten persistenten Execution aufgelöst.

## Zulässiger Attempt

Die Prüfung läuft nur für genau passende Fakten:

- Execution im Status `prepared`;
- Attempt im Status `prepared`;
- Attempt-Nummer 1;
- keine Finish-Zeit;
- Attempt gehört zur Execution;
- Execution gehört zum Handoff.

Unbekannte, bereits weitergeschaltete oder inkonsistente Fakten erzeugen kein
verifiziertes Payload.

## Interne Artifact-Bindung

Aus dem Handoff konstruiert der Integritätscheck intern eine
`ReleasePublicationArtifactBinding`.

Sie bindet:

- stabile Handoff-ID;
- Bundle-SHA-256;
- Signatur-SHA-256;
- Promotion-Evidence-SHA-256.

Nur diese intern erzeugte Bindung wird an die Artifact Source übergeben.

## Kontrollierte lokale Source

`BoundLocalReleasePublicationArtifactSource` erhält bei kontrollierter
Komposition eine kopierte Zuordnung exakter Bindungen zu lokalen Dateien.

Ein späterer Request kann keine freie URL oder Pfadsubstitution ergänzen.

Die Source akzeptiert nur reguläre, nicht symbolisch verlinkte Dateien. Der
Signaturdateiname muss exakt aus Bundle-Dateiname plus `.sshsig` bestehen.

Fehlende Bindung, fehlende Datei, Symlink, falscher Dateiname oder Lesefehler
werden detailfrei als technische Source-Nichtverfügbarkeit behandelt.

## Geladene Bytes

Die Source liefert ein repr-freies `ReleasePublicationArtifactBytes` mit:

- kontrolliertem Bundle-Dateinamen;
- vollständigen Bundle-Bytes;
- vollständigen SSHSIG-Bytes;
- vollständigen Promotion-Evidence-Bytes.

Pfade verlassen die Source nicht. Das Ergebnis enthält keine Credentials und
keine Providerkonfiguration.

## Direkte Hashprüfung

Vor jeder strukturellen oder kryptografischen Prüfung werden die vollständigen
geladenen Bytes erneut mit SHA-256 gehasht.

Bundle-, Signatur- und Evidence-Hash müssen exakt dem persistenten Handoff
entsprechen. Eine Abweichung ist eine neutrale fachliche Ablehnung und erzeugt
kein verifiziertes Payload.

Execution-seitig kopierter Bundle- und Signaturhash müssen zuvor exakt mit dem
Handoff übereinstimmen. Abweichende persistente Kontrollfakten sind technische
Nichtverfügbarkeit, nicht normale Ablehnung.

## Historische Promotion-Evidence

Die Evidence muss kanonisches JSON mit Abschluss-Newline sein und weiterhin
`promotable: true` tragen.

Sie wird mit den persistenten historischen Fakten verglichen:

- Bundle-, Checksum- und Signaturhash;
- Source Commit und Paketversion;
- Bundleformat;
- Signer und Key;
- damalige Policy-Revision;
- Promotion-Verifier;
- damaliger Entscheidungszeitpunkt;
- verified/current/promotable-Status.

Eine semantische Abweichung autorisiert keinen späteren Providerzugriff.

## Vollständige Bundle-Prüfung

Der bestehende LQ-236-Verifier prüft das vollständige Bundle erneut in Memory.

Damit gelten weiterhin unter anderem:

- sicherer einzelner Archivroot;
- kanonisches Manifest;
- vollständige SHA256SUMS-Bindung;
- unveränderte Wheel-Metadaten;
- lineare Migrationen bis Head `20260817_0022`;
- erwartete Operator-, Runbook-, Contract- und Example-Inventare;
- Secret- und Pfadgrenzen des Bundleformats.

LQ-255 definiert kein zweites Bundleformat.

## Detached SSHSIG

Die bestehende LQ-237-Prüfung verifiziert erneut:

- SSHSIG-Format und Größenlimit;
- Namespace `liquent-operations-release-v1`;
- Signer-Identität;
- Key-Fingerprint;
- detached Signatur über die im Bundle enthaltenen SHA256SUMS.

Die Signaturprüfung verwendet kontrollierte temporäre Dateien mit begrenztem
Lebenszyklus. Sie schreibt keine Artefakte in den Releasebestand zurück.

## Aktuelle Registry

Die Signatur wird nicht nur gegen die historische Evidence geprüft.

`CurrentReleaseAuthorityRegistryProjection` liefert genau einen aktuellen
System-of-Record-Snapshot. Aktuelle Policy, Signer und Key müssen weiterhin
aktiv sein.

Revocation, Expiry oder Deaktivierung nach Attempt-Erzeugung verhindert damit
eine spätere positive Integritätsentscheidung.

Es gibt keinen positiven Trust-Cache und keine Grace-Boolean.

## Wheel- und Checksum-Bindung

Der aus dem verifizierten Manifest aufgelöste Wheel-Hash muss exakt dem
persistenten Handoff entsprechen.

Der Hash der tatsächlich signierten SHA256SUMS muss ebenfalls exakt dem
Handoff entsprechen.

Damit werden alle fünf persistenten Artefakthashes bytegenau abgedeckt:

- Bundle;
- Wheel;
- SHA256SUMS;
- detached Signatur;
- Promotion-Evidence.

## Positives Ergebnis

Nur bei vollständiger Übereinstimmung entsteht
`VerifiedReleasePublicationArtifacts`.

Das Ergebnis bindet Execution, Attempt, Handoff, Paketversion, alle fünf
Hashes und die bereits geprüften Bytes.

Das Ergebnis selbst führt keine Zustandsänderung aus und gewährt keine
dauerhafte Publication-Authority. Ein späterer Provider-Schritt muss aktuelle
Regeln seines eigenen Slices weiterhin beachten.

## Neutrale Ablehnung

`None` deckt insbesondere ab:

- unbekannten oder nicht mehr vorbereiteten Attempt;
- geladene Bytes mit abweichenden Hashes;
- abweichende historische Evidence;
- ungültiges Bundle;
- ungültige detached Signatur;
- inzwischen inaktiven oder widerrufenen Signer oder Key;
- abweichenden Wheel- oder Checksum-Hash.

Die Antwort verrät nicht, welche Einzelprüfung abgelehnt hat.

## Technische Nichtverfügbarkeit

`ReleasePublicationArtifactSourceUnavailable` bleibt die detailfreie Grenze
der kontrollierten Dateiauflösung.

`ReleasePublicationArtifactIntegrityUnavailable` vereinheitlicht technische
Fehler des Gesamtchecks, darunter Datenbank-, Source-, Registry-Projektions-,
Krypto-Provider-, temporäre Datei- und beschädigte Persistenzfehler.

Beide Fehler tragen keine Pfade, IDs, Hashes, SQL-, Registry- oder
Kryptografiedetails.

## Persistenz und Migrationen

LQ-255 liest die bestehenden LQ-253/254-Fakten ausschließlich read-only.

Attempt, Execution, Handoff, Receipt und Reassessment werden nicht geändert.
Es gibt keine Migration, Tabelle oder Seed. Head bleibt `20260817_0022` mit 22
Migrationen.

## Nachweis

Tests belegen:

- vollständige positive Bundle-, Hash- und SSHSIG-Prüfung;
- neutrale Ablehnung mutierter Bundlebytes;
- Ablehnung semantisch abweichender historischer Evidence;
- Wirkung aktueller Key-Revocation auf spätere Entscheidungen;
- keine Source-Nutzung für unbekannte Attempts;
- Sperre ungebundener und symbolisch verlinkter Dateien;
- technische Behandlung inkonsistenter Execution-/Handoff-Hashes;
- denselben read-only Nachweis auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3148 passed, 116 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-255 implementiert keine Providerinspektion, Read-before-write,
Idempotency-Key-Übergabe, Upload, Create, Attempt-Transition, Unknown Outcome,
Reconciliation, Receipt, Reassessment, CLI, Credentials, Netzwerk-, Git- oder
Deploymentaktion.

## Nächster Slice

LQ-256 sollte die kontrollierte read-only Provider-Zielinspektion und deren
create-only Entscheidungsvertrag implementieren. Sie darf noch keinen Upload
ausführen und muss vorhandene gleiche, abweichende, fehlende und technisch
unklare Zielzustände strikt unterscheiden.
