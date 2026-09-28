# LQ-715 — Semantic Engine API Create Policy Contract

## Ziel

Eine klassifizierte Create-Route darf erst nach vollständiger semantischer
Validierung ihres kanonischen JSON-Bodys weiterleitbar werden.

## Kontrollierte Konfiguration

Die Policy wird an drei absolute, getrennte Nicht-Root-Wurzeln für Control,
Source und Target, zwei feste Wrappercommands sowie positive Wrapper-UID/GID
gebunden.

Diese Werte stammen später ausschließlich aus privater Proxykonfiguration.

## Exakter Body

Der Body enthält genau Image, Entrypoint, User, Labels und HostConfig in
kanonischer JSON-Kodierung ohne doppelte Schlüssel.

Das Image ist ausschließlich ein lowercase `sha256:`-Digest.

## Anker und Labels

Genau sechs Supervisorlabels sind erlaubt. Der feste Entrypoint wird durch den
bestehenden kanonischen Child-Ankercodec dekodiert.

Dokument-, Digest-, Creation-, Handle-, Directory-, Image- und Profilfakten
müssen zwischen Anker, Labels und Image exakt übereinstimmen.

## Securityprofil

User ist exakt die konfigurierte numerische Wrapperidentität.

Network none, private PID, read-only Root, CapDrop ALL, nicht privilegiert,
kein AutoRemove und Restart no/0 sind unveränderlich.

## Mountprofile

Control-Artefakte und Launchdatei liegen unter genau einem direkten Child der
Controlwurzel und haben feste Containerziele und Modi.

Writer erhält Source read-only und Target read-write unter den kontrollierten
Datenwurzeln. Recovery erhält nur Target read-only.

Zusätzliche, umsortierte oder wurzelfremde Mounts sind verboten.

## Grenzen

Die Policy prüft nur Daten. Dateiexistenz, Symlinks, Ownership und Modus bleiben
Hostpreflight; Listener, Forwarding und Daemonzugriff bleiben geschlossen.
