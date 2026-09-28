# LQ-753 — Engine API Verified Exchange Evidence

## Positive Evidenz

Ein gültiges Client-/Daemonpaar wird vollständig aus Kernelfakten geprüft, bevor
der erste Streamread erfolgt. Danach bleibt die bestehende bytegenaue
Requestweitergabe und kanonische Responseprojektion erhalten.

Beide Streamlebenszyklen bleiben extern.

## Negative Evidenz

Falsche Clientcredentials verhindern Daemonprüfung und jedes I/O. Falsche
Daemoncredentials erfolgen nach Clientprüfung, aber ebenfalls vor jedem I/O.

Verschiedene Streamobjekte mit gleicher Deskriptornummer, dasselbe Objekt in
beiden Rollen und ein nach der Policyprüfung wechselnder Fileno werden vor dem
Exchange abgelehnt.

Kernel-Ausnahmedetails werden nicht sichtbar und kein Stream wird geschlossen.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Listen, Bind, Accept, Connect, Settimeout oder
Close. Alle Tests verwenden bereits verbundene kontrollierte Streamdoubles.

Die Evidenz öffnet damit weder Clientlistener noch Daemonconnect.
