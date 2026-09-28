# LQ-280 — Owner-only Release Registry Bootstrap and Key Activation Operators

## Ergebnis

LQ-280 implementiert die zwei in LQ-278 definierten owner-only Prozessgrenzen:

- `liquent-release-registry-bootstrap`;
- `liquent-release-key-activation` mit `challenge` und `apply`.

Damit sind die ersten beiden der vier LQ-277-Betriebsblocker geschlossen.

Es gibt weiterhin keine automatische Aktivierung oder Runtime-Verdrahtung.

## Registry-Bootstrap

Der Bootstrap-Command akzeptiert ausschließlich private Pfade für Datenbank-
URL, kanonischen Ein-Feld-Request und ersten Ed25519-Public-Key.

Der Request enthält nur die stabile Bootstrap-ID. Der Public Key liegt in
einer getrennten Datei ohne Kommentar oder caller-gelieferten Fingerprint.

Der Operator berechnet den SHA-256-Fingerprint unabhängig mit OpenSSH.

## Interne Bootstrap-Fakten

Nach bestätigtem Migration-Head komponiert der Operator den vorhandenen
LQ-241-Adapter mit dem sicheren Materialgenerator.

Lifecycle-Authority-, Signer-Authority-, Key-, Registry-Revision- und Policy-
Revision-ID entstehen intern erst nach bestätigter vollständiger Leere.

Bootstrap erzeugt weiterhin einen inaktiven Key und keine Signatur.

## Geschützte Bootstrap-Ausgabe

Erfolg und exakter Retry liefern denselben kanonischen JSON-Shape mit Outcome,
Bootstrap-, Lifecycle-, Signer-, Key-, Registry- und Policy-ID.

Eine andere Bootstrap-ID nach sichtbarer Historie endet neutral
`not_bootstrapped`. Abweichende Wiederverwendung derselben ID bleibt Konflikt.

Die Ausgabe enthält weder Public Key noch Fingerprint, DSN oder Pfade.

## Aktivierungsrequest

Challenge und Apply verwenden dieselbe kanonische Requestdatei mit exakt:

- Lifecycle-Actor-Authority;
- stabiler Change-ID;
- erwarteter aktueller Registryrevision;
- inaktiver Key-ID.

Zusätzliche Allow-, Status-, Reviewer-, Public-Key- oder Ergebnisfelder werden
vollständig abgelehnt.

## Read-only Challenge-Lookup

`DatabaseReleaseKeyActivationChallenge` ergänzt eine read-only Sicht auf die
bereits normative LQ-242-Challengekonstruktion.

Der Lookup bestätigt aktuelle Policy, aktiven Lifecycle-Actor, inaktiven Key,
aktive Signer-Authority und exakte Current-Revision.

Er erzeugt keine Decision, Revision, Reservierung oder Statusmutation.

Bei neutral fehlender aktueller Bindung wird keine Datei materialisiert.

## Exklusive Challenge-Datei

Der Challenge-Modus akzeptiert einen absoluten, abwesenden Zielpfad in einem
owner-only Verzeichnis.

Die Bytes werden vollständig in eine exklusive private temporäre Datei
geschrieben, synchronisiert und über einen exklusiven finalen Hardlink
materialisiert. Vorhandene Ziele werden nicht geöffnet oder ersetzt.

stdout enthält nur `challenge_materialized` oder `not_challenged`.

## Fester Reviewer-Trust

Apply lädt Reviewer-Trust ausschließlich vom festen Systempfad:

```text
/etc/liquent/release-activation-reviewers.json
```

Es gibt keine CLI-Option, Requesteigenschaft oder Environmentvariable, die
diesen Pfad oder Trustsatz überschreibt.

Die kanonische owner-only Datei enthält eine nicht leere Reviewer-Liste mit
jeweils ID, Ed25519-Public-Key und SHA-256-Fingerprint.

Der Pfadparameter von `run_apply` existiert ausschließlich als interne
Composition-Seam für isolierte Tests; die installierte Prozessgrenze stellt
ihn nicht bereit.

## Proof und Approval

Proof- und Approval-Datei werden owner-only, descriptor-basiert, symlinkfrei
und auf jeweils 16384 Byte begrenzt gelesen.

LQ-279 prüft beide detached SSHSIGs über die intern rekonstruierte aktuelle
Challenge und getrennte Namespaces.

Reviewer-ID stammt ausschließlich aus dem eindeutig passenden festen Trustkey.

## Persistente Aktivierung

Bei positiver Kryptografie und weiterhin aktueller Authority ruft Apply genau
einmal `DatabaseReleaseKeyActivation.activate_key` auf.

Die resultierende Registryrevision wird intern kryptografisch erzeugt. Actor,
Key, erwartete Revision, Proof- und Approval-Hashes bleiben der stabile
persistente Decision-Fingerprint.

Exakter Retry liefert dieselbe Revision und Reviewer-ID ohne neue Verifikation
oder Generatorzüge.

## Ausgaben und Exitcodes

Bootstrap und Aktivierung verwenden dieselbe geschlossene Familie:

- Erfolg: Exit `0`;
- neutrale Nichtausführung: Exit `5`;
- Inputablehnung: Exit `2`;
- stabiler Konflikt: Exit `3`;
- technische Nichtverfügbarkeit: Exit `4`.

Fehlerausgaben enthalten ausschließlich stabile Codes. Interne IDs erscheinen
nur in den ausdrücklich geschützten erfolgreichen Resultaten.

## Readiness und Ressourcen

Beide Prozesse bauen pro Aufruf genau eine Engine aus der privaten URL-Datei.

Der exakte Migration-Head wird vor Mutation bestätigt. Kein Operator migriert,
adoptiert oder repariert den Bestand.

Engine und temporäre Kryptografiedateien werden in allen Pfaden geschlossen
beziehungsweise entfernt.

## Bundle-Inventar

Beide Commands sind additive Console Entry Points. Das operative Release-
Bundle erwartet nun 17 Entry Points.

Mit den zwei neuen Operatormodulen enthält das Wheel 16 Module unter der
Operatorgrenze einschließlich Package-Initialisierung und Worker-Composition.

Migrationenzahl und Bundleformat bleiben unverändert.

## Nachweis

Der integrierte Test führt aus einem leeren migrierten Bestand den echten
Bootstrap-Command aus, wiederholt ihn exakt, materialisiert die aktuelle
Challenge, erzeugt getrennte reale Ed25519-Proof- und Reviewer-Approval-
Signaturen und aktiviert den Key persistent.

Weitere Tests bestätigen geschlossene Requests, fehlende Trust-CLI-Auswahl,
Kryptografiegrenzen, Bundle-Inventar und bestehende Adaptersemantik.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit:

```text
3359 passed, 588 warnings
```

## Bewusst nicht enthalten

LQ-280 implementiert keinen Publication-Control-Plane-Bootstrap und keinen
autorisierten Publication-Handoff-Operator. Diese zwei LQ-277-Blocker bleiben.

Es entstehen keine neue Migration, Route, Settingsvariable, Service-Unit,
Scheduler-, CI-, Deployment-, Signing-, Promotion- oder Publicationaktion.

Der Head bleibt `20260819_0024` mit 24 linearen Migrationen.

## Folgeordnung

LQ-281 sollte den owner-only Publication-Control-Plane-Bootstrap-Vertrag
entscheiden und implementieren, einschließlich geschützter Übergabe seiner
vier stabilen Ergebnis-IDs an den späteren Handoff-Prozess.
