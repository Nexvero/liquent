# LQ-2629 — Staging Pre-Bootstrap Backup Verification

## Ergebnis

Der Ziel-VPS besitzt ein aktives OVH Automatic Backup. Der Wiederherstellungs-
punkt vom 4. September 2026, 18:53 UTC wurde über den OVH Manager
nicht-destruktiv bereitgestellt. Eine Wiederherstellung wurde nicht ausgelöst.

OVH stellte einen separaten 101-GB-Datenträger bereit. Dessen Root-Dateisystem
wurde auf dem VPS ausschließlich mit `ro,norecovery` eingebunden. Damit waren
weder Schreibzugriffe noch ext4-Journal-Replay zugelassen.

## Verifikation

Die Baseline-Dateien `/etc/os-release` und `/etc/hostname` waren lesbar und
wurden als unkritische Wiederherstellbarkeitsprobe mit SHA-256 geprüft. Der
Backupstand enthielt erwartungsgemäß noch kein `/opt/liquent`; er bildet damit
den Zustand vor der aktuellen Staging-Vorbereitung ab.

Der revisionsgebundene Nachweis liegt root-owned und Modus `0640` neben der
Release-Evidenz als `prebootstrap-backup.evidence`. Er enthält:

- eine VPS-, Zeit- und Provider-gebundene Snapshot-ID,
- den UTC-Verifikationszeitpunkt,
- die read-only Mountmethode und effektiven Mountoptionen,
- die beiden beobachteten Dateihashes,
- die explizite Abwesenheit der Liquent-Baseline.

Nach erfolgreicher Prüfung wurde der lokale Dateisystemmount entfernt und das
Unmounten der OVH-Bereitstellung angefordert.

## Grenze

Der Nachweis behauptet keine Datenbankwiederherstellung, da vor dem initialen
Bootstrap noch keine Liquent-Datenbank existiert. Er belegt den real lesbaren
VPS-Vorher-Zustand und ersetzt keine späteren regelmäßigen Datenbank- und
Artefaktbackups. Der separate Backup-Containervertrag bleibt weiterhin offen.
