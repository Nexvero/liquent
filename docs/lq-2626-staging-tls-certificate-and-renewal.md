# LQ-2626 — Staging TLS Certificate and Renewal

## Ergebnis

Nach bestätigter weltweiter DNS-Auflösung wurde über den bestehenden
nginx-Webroot ein öffentlich vertrauenswürdiges Let’s-Encrypt-Zertifikat für
`staging.liquent.ai` ausgestellt. Das OVH-Postfach `admin@liquent.ai` ist als
ACME-Kontakt hinterlegt. Das Zertifikat ist vom 5. September bis zum
4. Dezember 2026 gültig.

Die Bootstrap-Kopie liegt unter `/opt/liquent/edge/certs`. Fullchain und
privater Schlüssel gehören `root:root`; der Schlüssel ist Modus `0600`.
Hostname und kryptografische Übereinstimmung von Zertifikat und Schlüssel
wurden nach der Installation geprüft, ohne Schlüsselmaterial auszugeben.

## Erneuerungsvertrag

`install-staging-certificate.sh` schließt die Lücke zwischen Certbots
automatisch erneuerter Lineage und dem vom Edge read-only gemounteten
Zielverzeichnis. Der Hook:

- verlangt beide lesbaren Certbot-Lineage-Dateien,
- prüft SAN-Abdeckung und Schlüsselpaar vor jeder Zielmutation,
- installiert Fullchain und Schlüssel über private temporäre Dateien,
- setzt `0644` beziehungsweise `0600` sowie `root:root`,
- lädt nginx nur neu, wenn der geprüfte Edge-Compose-Vertrag vorhanden ist und
  der Edge-Dienst tatsächlich läuft.

Fehlt eine Voraussetzung, bleibt die bisher installierte Zielkopie erhalten.
Der Hook startet keinen gestoppten Edge und verändert keine DNS-, Mail- oder
Anwendungsdaten.
Der installierte Hook wurde gegen die echte Certbot-Lineage erfolgreich
ausgeführt. Zusätzlich bestand die vollständige simulierte ACME-Erneuerung mit
Certbots Staging-CA, ohne das produktive Zertifikat zu ersetzen.

## Grenze

TLS-Ausstellung und Zielkopie sind abgeschlossen. Der Edge-Container wurde
nicht gestartet. Übrige Infrastrukturpins, Laufzeitwerte und ein echter
frischer Backup-Nachweis bleiben Voraussetzungen des Online-Preflights.
