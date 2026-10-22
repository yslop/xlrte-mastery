# Lernpakete · Learning packs

Ein Lernpaket ist alles, was Mastery für eine Prüfung braucht. Die Engine bleibt gleich.
*A learning pack is everything Mastery needs for one exam. The engine stays the same.*

## Eigene Prüfung anlegen · create your own exam

Im Einrichtungs-Dialog „Eigene Prüfung anlegen“ wählen, oder im Terminal:

```bash
python3 _xlrte/scripts/new_pack.py --name "AWS Solutions Architect Associate" --short "AWS SAA" --lang en \
  --category "Secure architectures;30" --category "Resilient architectures;26" \
  --category "High-performing architectures;24" --category "Cost-optimised architectures;20" \
  --questions 65 --minutes 130 --pass 72
```

Das legt `_xlrte/packs/<id>/` an mit `pack.json`, `glossary.json`, `items.json` und einer Anleitung (`README.md`), wie du
das Paket mit deiner KI aus deinen eigenen Notizen füllst.

| Datei · file | Inhalt · content |
|---|---|
| `pack.json` | Name, Sprache, Prüfungsformat, Kategorien mit Gewicht, Lernziele (`id`, `cat`, `text`) |
| `glossary.json` | Begriffskarten `term`, `definition`, `los` – daraus entstehen täglich neue Übungen |
| `items.json` | Eigene Fragen `id`, `lo`, `q`, `options` (4), `answer` (Index), `why` |

## Täglich neue Übungen · daily drills

`_xlrte/scripts/gen_drills.py` erzeugt jeden Tag deterministisch neue Fragen aus den Begriffskarten (Begriff ↔
Beschreibung, Ablenker aus derselben Kategorie, schwächste Lernziele zuerst). Der Tageslauf ruft es automatisch auf.
Je mehr gute Karten ein Paket hat, desto mehr Übung entsteht.

## Mitgeliefert · included

| Paket | Sprache | Inhalt | Status |
|---|---|---|---|
| PMP (ECO 2026) | EN | 261 Fragen + 180 (Mock 1) + 60 (Fallen-Mock 2), 11 Fallstudien, 224 Karten, Fallen-Radar | Community-Review |
| ITIL 5 Foundation – Muster | DE | 127 Fragen + 2 Schattenprüfungen à 40; Lernziel-IDs und Gewichte, keine Lehrplantexte | Muster |
| Scrum-Grundlagen | DE | 18 Fragen, 18 Karten | Beispiel |

## Ein Paket beisteuern · contribute a pack

1. Issue mit Label `pack`: Prüfung, Sprache, öffentlich zugängliches Prüfungsprofil, wer fachlich prüft.
2. Nur eigene Formulierungen. Keine Prüfungsfragen, keine Buch- oder Kurstexte.
3. Pflicht je Frage: Lernziel, Erklärung, warum die anderen Optionen falsch sind.
4. `python3 _xlrte/scripts/xlrte.py check` muss sauber durchlaufen.
