# LQ-279 — Fixed Release Key Proof and Approval Verification

## Ergebnis

LQ-279 implementiert die konkrete Kryptografie- und Composition-Grenze für den
LQ-278-Key-Aktivierungsprozess.

Proof of Possession und unabhängiges Approval sind detached Ed25519-SSHSIG über
exakt dieselben kanonischen LQ-242-Challengebytes.

Getrennte feste Namespaces verhindern die Umdeutung eines Proofs als Approval
oder eines Approvals als Release-Signatur.

## Feste Namespaces

Der Key-Proof verwendet ausschließlich:

```text
liquent-release-key-possession-v1
```

Das unabhängige Approval verwendet ausschließlich:

```text
liquent-release-key-activation-approval-v1
```

Namespace, Algorithmus und Signaturformat sind keine Request- oder
Konfigurationsfelder.

## Proof-Format

Proofbytes müssen exakt ein kanonisches OpenSSH-SSHSIG-Armor mit finalem LF
und höchstens 16384 Byte sein.

Der Verifier erhält den Public Key ausschließlich aus dem persistenten
LQ-242-Lookup und prüft die Signatur über die unveränderten Challengebytes.

Ein veränderter Challenge-Bytewert, falscher Namespace, anderer Key,
angehängte Bytes oder nicht kanonisches Armor endet neutral `False`.

## Approval-Format

Approvalbytes verwenden dasselbe begrenzte kanonische SSHSIG-Format, werden
aber unter dem eigenen Approval-Namespace signiert.

Die Approval-Datei enthält keine Reviewer-ID, Rolle, Capability, Allow-
Entscheidung, Public Key oder Trustkette.

Reviewer-Identität entsteht ausschließlich durch den eindeutig passenden
Schlüssel des beim Composition-Aufbau fest gebundenen Trustsatzes.

## Fester Reviewer-Trust

Jeder Trusteintrag bindet repr-frei:

- stabile `ReleaseActivationReviewerId`;
- kanonischen `ssh-ed25519` Public Key ohne Kommentar;
- kanonischen SHA-256-Fingerprint.

Reviewer-ID, Fingerprint und Public Key müssen im Trustsatz jeweils eindeutig
sein. Ein leerer oder doppelter Trustsatz wird beim Aufbau abgelehnt.

Der Trustsatz wird als bereits kontrollierte Composition-Eingabe übernommen,
nicht aus Aktivierungsrequest, Proof, Approval oder Datenbankantwort gelesen.

## Unabhängige Fingerprintprüfung

Vor jeder Approval-Verifikation berechnet die OpenSSH-Grenze den Fingerprint
des gebundenen Reviewer-Public-Keys erneut.

Nur bei exakter Übereinstimmung wird die detached Signatur geprüft. Ein
abweichender Fingerprint führt neutral zu keinem Reviewer.

Damit kann ein falsch gebundener Key nicht allein durch passende ID oder
Signaturbytes Reviewer-Authority erhalten.

## Eindeutige Reviewer-Auflösung

Der Approval-Verifier prüft ausschließlich die fest gebundenen Reviewer.

Genau ein erfolgreicher Match liefert dessen stabile Reviewer-ID. Null oder
mehrere Matches liefern neutral `None`.

Eine im Approval behauptete Identität ist strukturell nicht darstellbar.

Die bestehende LQ-242-Persistenzgrenze sperrt zusätzlich dieselbe Reviewer-ID
wie den Lifecycle-Actor.

## Composition

`compose_release_key_activation_verification` baut gemeinsam:

- `OpenSshReleaseKeyProofVerifier`;
- `OpenSshReleaseKeyActivationApprovalVerifier`.

Der Aufbau validiert nur den festen Trustsatz und führt kein subprocess-,
Datei-, Datenbank-, Clock- oder Netzwerk-I/O aus.

Die resultierende Composition ist repr-frei und besitzt keine mutierbare
Requestkonfiguration.

## OpenSSH-Ausführung

Verifikation verwendet ausschließlich argv-basierte `ssh-keygen`-Aufrufe ohne
Shell.

Public Key, `allowed_signers` und SSHSIG werden in einem eindeutig erzeugten
temporären Verzeichnis mit Modus `0600` materialisiert.

Die Challengebytes werden über stdin an `ssh-keygen -Y verify` übergeben und
nicht in Logs oder Commandargumente aufgenommen.

Temporäre Dateien und Verzeichnisse werden nach jedem Aufruf entfernt.

## Ablehnung und Nichtverfügbarkeit

Kryptografisch falsche, nicht kanonische oder nicht passende Signaturen sind
neutrale negative Verifikation.

Fehlendes `ssh-keygen`, Prozessstartfehler, unlesbare Ausgabe und fehlgeschlagene
Fingerprintberechnung sind detailfreie technische
`ReleaseKeyActivationVerificationUnavailable`.

stderr, subprocess-Ausgabe, Dateipfade, Public Keys und Signaturbytes verlassen
die Grenze nicht.

## Keine positive Caches

Proof und Approval werden für jede neue LQ-242-Entscheidung erneut gegen die
übergebenen Challengebytes geprüft.

Die Composition speichert kein positives Ergebnis, keine Challenge und keinen
Reviewer-Match.

Persistierter exakter Retry bleibt unverändert Aufgabe des LQ-242-Adapters und
überspringt dort beide Verifier.

## Persistente Integration

Der integrierte Test erzeugt getrennte Ed25519-Keys für Signing-Key-Besitz und
Reviewer-Approval.

Er baut einen echten initialen Registry-Snapshot, signiert die intern exakt
rekonstruierte LQ-242-Challenge unter beiden Namespaces und übergibt beide
konkreten Verifier an `DatabaseReleaseKeyActivation`.

Die Aktivierung committet eine neue Registryrevision und übernimmt ausschließlich
die aus festem Trust kryptografisch aufgelöste Reviewer-ID.

## Keine Authority-Ausweitung

Ein gültiger Proof bestätigt nur Besitz des bereits registrierten privaten
Keys. Er erteilt keine Lifecycle- oder Signing-Authority.

Ein gültiges Approval ersetzt weder aktiven Lifecycle-Actor noch aktuelle
Revision, aktiven Signer oder inaktiven Keyzustand.

Beide positiven Kryptografiefakten sind gemeinsam notwendig, aber nicht allein
hinreichend für den persistenten Commit.

## Bewusst nicht enthalten

LQ-279 implementiert keinen CLI-Parser, Challenge-Datei-Writer, Bootstrap-
Operator, Aktivierungsoperator, Trustdatei-Loader oder Runbook.

Es entscheidet keine HSM-, Agent-, KMS-, CA-, Secret-Manager- oder Remote-
Approval-Anbindung und erzeugt keine privaten Schlüssel.

Es fügt keine Tabelle, SQL, Migration, Route, Entry Point, Service-, Scheduler-,
CI-, Deployment-, Signing-, Promotion- oder Publication-Aktivierung hinzu.

Der Head bleibt `20260819_0024` mit 24 linearen Migrationen. Das operative
Bundle bleibt bei 15 Console Entry Points und unverändertem Operatorinventar.

## Nachweis und Folgeordnung

Tests belegen echte Ed25519-Proof- und Approval-Signaturen, Challenge- und
Namespacebindung, kanonische Größenbegrenzung, festen eindeutigen Reviewer-
Trust, Fingerprintprüfung, detailfreie Tool-Nichtverfügbarkeit und die
vollständige persistente Aktivierung.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit:

```text
3357 passed, 588 warnings
```

LQ-280 sollte nun die beiden in LQ-278 definierten owner-only Operatoren für
Registry-Bootstrap sowie Challenge/Apply-Key-Aktivierung implementieren und
diese feste Composition ohne caller-wählbaren Reviewer-Trust verwenden.
