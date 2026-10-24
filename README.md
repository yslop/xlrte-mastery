# XLRTE Mastery · Prüfungen bestehen, Wissen behalten

[English](README.en.md) · Teil von [yslop](https://github.com/yslop): *why slop?* Werkzeuge für alle, die lieber gründlich als viel machen.

![Mastery in 25 Sekunden: ehrliche Prognose, Schwachstellen-Drill mit Quelle und „Frage melden“, Lernpfad, Tages-Recap](docs/media/mastery_de.gif)

**XLRTE Mastery ist ein lokales Lern-Cockpit für jede Prüfung.** Es misst, was du wirklich beherrschst, statt abzuhaken,
was du gelesen hast: Jede Antwort ist ein Beleg, Wiederholung kommt dann, wenn du sonst vergessen würdest, und die
Prognose sagt ehrlich, wie nah du an der Bestehensgrenze bist.

> Wissen gehört allen. Wer sich heute weiterbildet, muss schneller lernen als je zuvor, oft neben Job, Familie oder
> Jobsuche. Mastery nimmt dir die Verwaltung ab, damit deine Zeit ins Verstehen geht.

<!-- HERO: 30-Sekunden-GIF Cockpit → Schwachstellen-Drill → Prognose (docs/hero.gif) -->

## Was drin ist

- **Jede Prüfung:** Wähle ein Lernpaket oder lege im Einrichtungs-Dialog deine eigene Prüfung an (Kategorien, Gewichte,
  Fragenzahl, Zeit, Bestehensgrenze). Siehe [PACKS.md](PACKS.md).
- **Neue Übungen jeden Tag, ohne KI:** Aus den Begriffskarten deines Pakets erzeugt Mastery täglich neue Fragen, schwächste
  Lernziele zuerst. Deterministisch: derselbe Tag ergibt dieselben Fragen, der nächste Tag neue. Für PMP kommen
  Rechenübungen (Earned Value, PERT) mit neuen Zahlen dazu.
- **Ehrliche Messung:** Beherrschung je Lernziel aus deinen Antworten, mit Halbwertszeit. „Geraten und richtig“ zählt nur
  halb, „sicher und falsch“ wird zuerst wiederholt.
- **Tages-Recap:** Am Abend vergleicht Mastery deinen Tag mit deinem bisherigen Lernzeitraum: Abrufe, Trefferquote,
  Lernzeit, Fehler gegen Durchschnitt, letzte 7 Tage und Bestwert.
- **KI als Tutor, nicht als Orakel:** ein Lern-Prompt für Gemini Notebook, NotebookLM oder deine KI, der aus deinem echten
  Lernstand arbeitet. Deutsch und Englisch.
- **Deutsch und Englisch:** Oberfläche umschaltbar (unten links), Einrichtung in beiden Sprachen.

## Lernpakete

| Paket | Sprache | Inhalt |
|---|---|---|
| PMP (ECO 2026) | EN | über 500 eigene Fragen inkl. zweier Mock-Prüfungen, 11 Fallstudien, über 200 Begriffskarten, Fallen-Radar |
| ITIL 5 Foundation – Muster | DE | über 200 eigene Fragen inkl. zweier Schattenprüfungen; Vorbild für Prüfungen mit veröffentlichtem Lehrplan |
| Scrum-Grundlagen – Beispiel | DE | kleines Paket, zeigt das Format |
| Deine eigene Prüfung | beliebig | Gerüst aus dem Einrichtungs-Dialog, gefüllt mit deinen eigenen Formulierungen |

## In fünf Minuten startklar

Voraussetzung: Python 3.9 oder neuer.

```bash
git clone https://github.com/yslop/xlrte-mastery.git
cd xlrte-mastery
./mastery                  # Windows: mastery.cmd
```

Beim ersten Start öffnet sich der **Einrichtungs-Dialog** (lokal, 127.0.0.1): Paket oder eigene Prüfung, Termin,
Lernrhythmus, KI-Anbindung. Danach öffnest du `XLRTE_Cockpit.html`. Jeden Lerntag startest du mit `./mastery`.

Zum Ausprobieren lädt „Mit Beispiel-Lernverlauf starten“ drei Wochen erfundener Übungsdaten (Lernende „Sam Beispiel“).
Entfernen mit `python3 demo/load_demo.py --remove`.

## Datenschutz: Governance by Design

Alles läuft lokal. Kein Konto, keine Telemetrie. Deine KI wählst du selbst (Abo, eigener Schlüssel, EU-Anbieter oder
lokales Modell); „Nur lokal“ sperrt jeden entfernten Anbieter. Details: [PRIVACY.md](PRIVACY.md).

## Inhalte und Marken

Alle Fragen sind **eigene Formulierungen**, keine Prüfungsfragen und keine Texte aus Büchern oder Kursunterlagen. Sie
können Fehler enthalten: Melde sie über ein Issue mit dem Label `content`. PMI, PMP und PMBOK sind eingetragene Marken des
Project Management Institute, Inc.; ITIL ist eine eingetragene Marke von PeopleCert. XLRTE Mastery ist mit keiner dieser
Organisationen verbunden. Siehe [NOTICE.md](NOTICE.md).

## Mitmachen und Pilot

Am meisten hilft: Fragen prüfen und verbessern, neue Lernpakete, Übersetzungen. [CONTRIBUTING.md](CONTRIBUTING.md) ·
Pilotphase: [docs/PILOT.md](docs/PILOT.md) · Fragen und Ideen: GitHub Discussions.

## Lizenz und Herkunft

Code: [MIT](LICENSE). Lerninhalte: [CC BY-SA 4.0](CONTENT_LICENSE.md). XLRTE Mastery ist ein Projekt von **XLRTE**
(Prasanna Easwarananthan), entstanden aus der eigenen Prüfungsvorbereitung.
