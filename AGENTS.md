# Regeln für KI-Agenten in diesem Ordner (XLRTE Mastery)

1. Lies `_xlrte/RUNBOOK_LERNTAG.md`, bevor du etwas änderst.
2. `_xlrte/state/events.csv` ist die einzige Quelle der Wahrheit für den Lernstand. Nur anhängen, nie umschreiben.
3. Erfinde keine Lernstände. Prozentwerte kommen aus dem Lernprofil, das der Tageslauf schreibt.
4. Neue Fragen nur als Kandidaten (`data/items_candidates.json`), nie direkt in die Kernbank. Keine Texte aus Büchern,
   Kursunterlagen oder Prüfungen.
5. Datenschutz: Wenn `config/settings.json` „local_only“ enthält, nutze keine entfernten Dienste.
