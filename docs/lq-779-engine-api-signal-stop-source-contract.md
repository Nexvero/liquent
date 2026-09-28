# LQ-779 — Engine API Signal Stop Source Contract

## Ziel

Ein Prozesslauf erhält eine explizit besessene lokale Stopquelle für SIGTERM und
SIGINT, ohne globale Wirkung bei Import oder Konstruktion.

## Installation

Nur ein expliziter `install`-Aufruf im Main Thread darf Handler verändern. Vor
jeder Mutation werden beide bestehenden Handler vollständig gelesen und lokal
gebunden.

SIGTERM wird vor SIGINT installiert. Eine partielle Installation stellt bereits
veränderte Handler in umgekehrter Reihenfolge best-effort wieder her und endet
detailfrei.

Eine zweite Installation ohne vorheriges Restore ist verboten.

## Handler

Der installierte Handler setzt ausschließlich einen lokalen booleschen
Stopzustand. Er führt kein I/O, Logging, Close, Raise, Callback oder Chaining aus.

Nur SIGTERM und SIGINT wirken und nur während aktiver Installation. Der
Stopzustand ist monoton bis zum Restore und wird bei einer neuen Installation
zurückgesetzt.

## Restore

`restore` versucht beide ursprünglichen Handler in umgekehrter Reihenfolge
wiederherzustellen, auch wenn die erste Wiederherstellung fehlschlägt.

Danach ist die Quelle inaktiv. Restorefehler bleiben technische
Nichtverfügbarkeit; ein zweites Restore ist verboten.

## Grenzen

Die Quelle sendet keine Signale, startet keinen Thread und unterbricht kein
bereits blockierendes Accept. Sie wird später ausschließlich zwischen
Einzelaustauschen gelesen.
