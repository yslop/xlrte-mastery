"""PMP Fallen-Radar: Taxonomie und automatische Vorschläge (Spec 2026-10-03-fallen-radar-design.md)."""
import re

TAXONOMY = [
    {"id": "kw", "name": "Signalwort",
     "rule": "Frage nach FIRST, BEST, NEXT, MOST, LEAST oder NOT: erst die Frageform bestimmen, dann antworten."},
    {"id": "act", "name": "Voreiliges Handeln",
     "rule": "Bevor gehandelt wird, wird analysiert, gefragt oder geklärt."},
    {"id": "esc", "name": "Eskalation",
     "rule": "Zuerst auf der niedrigsten Ebene lösen; eskalieren, wenn Befugnis oder Versuche erschöpft sind."},
    {"id": "appr", "name": "Agil/Predictive vermischt",
     "rule": "Vorgehen zum Ansatz passend wählen: Backlog statt Change Board im Sprint, Selbstorganisation statt Zuweisung."},
    {"id": "term", "name": "Begriffsverwechslung",
     "rule": "Ähnliche Begriffe sauber trennen (Issue/Risk, Crashing/Fast Tracking, Validate/Control Scope, Secondary/Residual)."},
    {"id": "calc", "name": "Rechnen",
     "rule": "Richtige Formel, richtige Größe, Einheiten prüfen (EVM, Kanäle, kritischer Pfad, EMV)."},
    {"id": "multi", "name": "Mehrfachauswahl",
     "rule": "Alle geforderten Optionen müssen stimmen; ein Teiltreffer zählt nicht."},
    {"id": "role", "name": "Rollen und Entscheidungsrechte",
     "rule": "Wer entscheidet was: Projektmanager, Product Owner, Sponsor, Change Board, Funktionsmanager."},
    {"id": "eth", "name": "Ethik-Reflex",
     "rule": "Bei Interessenkonflikt, Geschenk, Fehler, Vertraulichkeit oder Druck zur Schönfärberei: Fakten klären, offenlegen oder an die zuständige Stelle melden, nie vertuschen, nie Vergeltung, dann weiterarbeiten."},
]
IDS = [t["id"] for t in TAXONOMY]

_KW = re.compile(r"\b(FIRST|BEST|NEXT|MOST|LEAST|NOT|EXCEPT|PRIMARY)\b")
_CALC_ABBR = re.compile(r"\b(CPI|SPI|EAC|ETC|TCPI|VAC|EMV|BAC|EV|PV|AC)\b")
_CALC_WORD = re.compile(r"\b(float|channels?|critical path|variance)\b", re.I)
_NUM_OPT = re.compile(r"^[-+]?\d[\d.,]*( days?| %| percent)?$")


def auto_traps(item):
    """Vorschlag nach festen Regeln: nur multi, calc und kw sind aus dem Text sicher erkennbar."""
    out = []
    if item.get("type") == "multi":
        out.append("multi")
    opts = [str(o).strip() for o in item.get("options", [])]
    q = item.get("q", "")
    if (len(opts) >= 3 and all(_NUM_OPT.match(o) for o in opts)) or _CALC_ABBR.search(q) or _CALC_WORD.search(q):
        out.append("calc")
    if _KW.search(q):
        out.append("kw")
    return out
