# LQ-2624 — Staging Release Evidence Intake

## Ergebnis

Das erfolgreiche GitHub-Actions-Artefakt des Release-Laufs `33968040510`
wurde aus der authentifizierten Projektansicht übernommen und vor der
Staging-Ablage vollständig geprüft. Der von GitHub ausgewiesene
Artefakt-SHA-256 ist bytegleich zum heruntergeladenen ZIP:

`f2d3ab77e31bcbd2ed366c48259e99761478c446e1c9ac9e82711392387678a1`

## Gebundene Identität

- Version: `0.1.0`
- Revision: `b2a277d763618a6bb51929375c9397f720f764a9`
- Image: `ghcr.io/nexvero/liquent`
- Image-Digest: `sha256:ba56aaae6a32f48987895899b7ec1c342a612073e0f20d9243515e374a1af27c`
- Manifest-SHA-256: `d9801ece012e490aba0eabddc5779fb733518e274d8cdc86edf5ae4e32bc3ed4`
- SBOM-SHA-256: `76fa0ea8d52e4d687d24df0e80d865da2b12ddc6ec6bc0b7d88a9d2751b12fef`
- Grype-Ergebnis-SHA-256: `69c1280d33a13d8325329b53ad07a8208d591f874818edb7c551a22a77ed5c3e`

Das Manifest bindet denselben SBOM-Hash. Der Scan enthält keinen High- oder
Critical-Befund; ein Medium-Befund bleibt als unveränderte Release-Evidenz
erhalten.

## Staging-Verwahrung

Manifest, SBOM und Scanergebnis liegen auf dem Ziel-VPS unter dem
versions- und revisionsgebundenen Verzeichnis
`/opt/liquent/releases/0.1.0-b2a277d763618a6bb51929375c9397f720f764a9`.
Verzeichnis und Dateien gehören `root`; die Dateien sind Modus `0640`. Die
nach der Übertragung erneut berechneten drei Hashes stimmen mit der lokalen
verifizierten Quelle überein.

## Grenze

Diese Übernahme startet oder zieht kein Image und erzeugt keine Secrets,
Zertifikate, Datenbank, Container oder Backup-Behauptung. Offen bleiben die
Freigabe der Infrastruktur-Digests, TLS, owner-only Laufzeitwerte und ein
echter frischer verifizierter Backup-Nachweis vor dem Online-Preflight.
