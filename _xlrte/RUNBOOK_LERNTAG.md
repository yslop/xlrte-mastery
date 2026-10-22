# RUNBOOK — geplanter Lauf „XLRTE Lerntag“

Dieser Lauf ist bewusst mechanisch, damit ihn ein kleines, günstiges Modell zuverlässig ausführt.
Signal → Skript → Datei. **Wenn ein Schritt nicht eindeutig ist: nicht raten, im Lauf-Bericht als `UNKLAR` nennen.**

Ordner-Wurzel: `_xlrte` (im Linux-Shell des Macs: `$HOME/mnt/Lernordner/_xlrte`)
Zeitpunkt: Mo–Fr 06:30 (vor dem Teams-Login um 09:00). Ein zweiter Lauf um 17:15 ist optional (Recap für das Lernjournal).

---

## Kontextregel (Token-Ökonomie)

Lies in einem normalen Lauf **ausschließlich**:

1. die JSON-Ausgabe von `python3 scripts/xlrte.py run`
2. die JSON-Ausgabe von `python3 scripts/xlrte.py gen-queue` (nur Schritt 3)
3. bei Schritt 1: die Titelliste neuer Mitschriftn

**Niemals** Lehrbuch, Handout, Glossar, Syllabus-PDF, `state/events.csv` oder alte Briefings selbst lesen.
Die Python-Engine rechnet deterministisch; das Modell schreibt nur in Schritt 3 (Fragen-Kandidaten) und Schritt 5 (Bericht).
Zielquote: ≥ 80 % der Inbox-Zuordnungen deterministisch (`deterministic_ratio`), TypeSafe nur für mehrdeutige Abschnitte.

---

## Schritt 0 — Vorprüfung

```bash
cd "$HOME/mnt/Lernordner/_xlrte"
python3 scripts/xlrte.py check
python3 scripts/xlrte.py eco-gate      # Konformität des Bestands mit dem ECO 2026 (nur Befund, bricht nichts ab)
```
Exit 1 → Fehlerzeilen in den Bericht übernehmen, trotzdem weitermachen (der Lauf selbst schreibt keine Inhalte um).

## Schritt 1 — Neue Unterlagen einsammeln (optional, nur wenn Mitschriftverbunden ist)

Mitschrift: Aufnahmen seit dem letzten Lauf auflisten (`state/runs.csv`, letzte Zeile = letzter Lauf).
Nur Aufnahmen, deren Titel eines dieser Wörter enthält: `ITIL`, `PMP`, `PMI`, `Kursanbieter`, `Classroom`, `Mentoring`, `Training`, `Lern`.
Je Treffer das Transkript als Klartext speichern: `inbox/Mitschrift/JJJJ-MM-TT_<titel-kurz>.txt`. Keine Zusammenfassung schreiben, keine Inhalte interpretieren.
Materialien, die der Mensch selbst ablegt (Folien, PDFs, Mitschriften), liegen bereits in `inbox/`.

## Schritt 2 — Deterministischer Lauf

```bash
python3 scripts/xlrte.py run
```
Macht in dieser Reihenfolge: Journal-Exporte aus `journal/` zusammenführen (→ `journal/_merged/`, nichts wird gelöscht) ·
Inbox anreichern (Textauszug → Lernziel; Stichwortindex, bei Mehrdeutigkeit TypeSafe `choice` mit Schwellen 0,75 / 0,65, Fehler → fail open) ·
Readiness, Mastery, EVM, fällige Wiederholungen · Briefing `notebooklm/JJJJ-MM-TT_Briefing.md` ·
Lernjournal `notebooklm/XLRTE_Lernjournal.md` · notes-vault-Notizen `bridge/to-notes-vault/` · `../XLRTE_Cockpit.html`.

Gibt es neue Kurs-Zusammenfassungen (`*-Summary.pdf`, z. B. rotiert nach `inbox/_verarbeitet/<Datum>/`), danach einmal `python3 scripts/course_notes.py` (Kursnotizen je Task, deterministisch).

## Schritt 3 — Neue Fragen für die Schwächen (einziger generativer Schritt, gehärtet)

**Maßgabe: Das ECO 2026 (`data/eco_pmp2026.json`) ist verbindlich.** Jede neue Frage dient genau einem ECO-Enabler. Bücher, Kurs und Trainer ergänzen, aber bei Widerspruch gilt das ECO.

```bash
python3 scripts/xlrte.py gen-queue
```
Ist PMP die aktive Prüfung, liefert der Befehl bis zu 10 Ziele, ausgewählt aus den **Schwächen** (schwächste Aufgaben zuerst), unabgedeckten Enablern und der Ansatz-Bilanz (40 % predictiv, 60 % agil/hybrid). Jedes Ziel enthält: `lo`, `en` (Enabler-ID, Pflicht), `en_text`, `appr` (Ziel-Ansatz), `weak`, `avoid_stems` (bereits vorhandene Stämme: nicht wiederholen), `course_notes` (Kontext, ungeprüft), `pmbok8` (Verweise, kein Text). Lies nichts weiter.

Schreibe **je Ziel genau eine** neue Frage, englisch, situativ („What should the project manager do FIRST/NEXT?“), PMI-Mindset, Bloom 2:
- **Länge des Fragetexts: 45–60 Wörter** (Ziel `stem_words`; Prüfungskaliber laut Trainer, vgl. HANDOVER 09.10.). Aufbau: Rolle und Projektlage (Ansatz, Branche), Auslöser/Problem, eine Einschränkung oder Nebeninformation, dann die Frage. Unter 35 oder über 110 Wörtern verwirft `add-candidates` die Frage. Die Optionen bleiben knapp (8–20 Wörter).
- Genau 4 Optionen, eine richtig. Optional `type: "multi"` (genau 5 Optionen, `answer` = Liste ≥ 2, Frage endet mit „(Choose two.)“), höchstens 1 von 10.
- Pflichtfelder: `exam:"pmp"`, `lo`, `en` (aus dem Ziel), `appr` (aus dem Ziel), `bl:2`, `q`, `options`, `answer`, `why` (1–2 Sätze: warum richtig, warum der stärkste Distraktor falsch), `source:"daily"`.
- Rechenfragen: `why` beginnt mit „Solution: … = … → Ergebnis“. Nachrechnen, bevor du schreibst.
- **Längen-Hinweis vermeiden, in beide Richtungen:** die richtige Option darf nicht systematisch die längste (oder kürzeste) sein. Verlängere die Distraktoren auf ähnliche Länge. Lösungspositionen A–D über den Stapel verteilen.
- Eigene Formulierung. Keine Sätze aus Buch, PMI-Glossar, Kursnotizen oder Übungsfragen übernehmen (der Zitatschutz verwirft Fenster ab 8 gleichen Wörtern).
- Keine Fallstudien (`case`), keine Fragen aus SP1/SP2/Mastery Builder/Trainer-Sets nachbauen.

Als JSON-Liste nach `/tmp/xlrte_candidates.json`, dann:
```bash
python3 scripts/xlrte.py add-candidates --file /tmp/xlrte_candidates.json
python3 scripts/xlrte.py render
```
`add-candidates` prüft hart: Enabler gehört zum Task, 4/5 Optionen, `why`, **Beinahe-Dublette** zu vorhandenen Fragen, **wörtliches Zitat** aus Lizenzmaterial, **Längen-Hinweis im Stapel**. Abgelehnte Einträge stehen mit Grund in der Ausgabe: **einmal** gezielt überarbeiten (nur die abgelehnten, Grund beheben) und erneut einreichen; schlägt es wieder fehl, im Bericht nennen und nicht weiter versuchen. Kandidaten erscheinen im Cockpit als „neu · ungeprüft“ (Training → „Neue Fragen“); der Mensch übernimmt oder verwirft sie.
Ist ITIL aktiv, gilt der bisherige Ablauf (deutsch, PeopleCert-Stil, höchstens 8 Einträge aus den frischen Auszügen).

## Schritt 4 — Gemini Notebook (optional)

Wenn Google Drive verbunden **und** `config.json → lernjournal_gdoc_id` gesetzt ist: den Inhalt von `notebooklm/XLRTE_Lernjournal.md` in dieses Google Doc schreiben (ersetzen). Das Notebook synchronisiert die Quelle dann per Klick.
Sonst: nichts tun – die Markdown-Datei ist die Quelle.
Das Lernjournal enthält oben das **Lernprofil** (Ledger-Werte für die Lern-Engine) – deshalb nach jedem Lauf synchronisieren; nicht von Hand ändern.

## Schritt 5 — Lauf-Bericht (kurz, deutsch)

1. Prognose ITIL 5 (`readiness_itil5`) und PMP ab 05.10. (`readiness_pmp`): Punkte / Bestehenswahrscheinlichkeit / Evidenzabdeckung
   · Study Hall (`studyhall`): Einträge / letzte Full-Length (nur Zahlen, nie Inhalte; Mastery-Beleg nur mit Domänen- oder Task-Werten)
2. Journal: übernommene Events; **0 Events an einem Werktag = Hinweis „Journal-Export fehlt“**
   · `empty` / `invalid` > 0 → Hinweis „Export abgebrochen – im Cockpit (Journal) „Jetzt exportieren“ klicken“; die Dateien liegen dann in `journal/_defekt/` (kein Datenverlust, Events bleiben im Cockpit ausstehend) · `date_fixed` > 0 nennen
3. Inbox: Dateien, Abschnitte, deterministisch / TypeSafe / UNKLAR, `deterministic_ratio`
4. Kandidaten: Ziele (Task/Enabler), hinzugefügt / abgelehnt mit Gründen; ECO-Gate (`eco_gate` in der `run`-Ausgabe: Enabler abgedeckt, Domänenanteile, Befunde)
5. Fällig: Prüfungstermin nicht gebucht (`booked=false` und < 10 Tage bis Zieltermin) · Musterprüfung fällig laut Tagesplan
6. UNKLAR-Liste

## Was der Lauf nie tut

- Das ECO 2026 oder Blueprint-Zahlen „anpassen“ · Fragen ohne Enabler-ID anlegen · Texte aus Buch, Glossar, Kursnotizen oder Übungsfragen wörtlich verwenden
- Dateien löschen (organisieren, nie löschen) · `state/events.csv` von Hand ändern
- Inhalte aus Lehrbuch, Handout oder Musterprüfungen in Fragen kopieren oder veröffentlichen
- Anwesenheit im Teams-Formular melden – das macht der Mensch; das Cockpit liefert nur den Text
- Stufen, Ergebnisse oder Lernzeiten „schätzen“ – nur Events zählen
