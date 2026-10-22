#!/usr/bin/env python3
"""Lab (Prototyp): Sokratischer Tutor und Propositions-Tabelle fuer beliebige Themen.

Modellfrei: das Skript baut Prompts (fuer Gemini/Claude) und prueft/verwertet die Antwort. Es ruft kein Modell auf.
  lab.py tutor TOPIC [--level auto|child|highschool|academic] [--source DATEI]
  lab.py multilevel TOPIC
  lab.py focus [--n 4] [--out DATEI]            # Fokus-Paket aus dem Lernstand (nur in der Drive-Kopie, braucht xlrte + Daten)
  lab.py basis                                  # die drei Basis-Prompts mit {THEMA}
  lab.py props DATEI                      # Prompt fuer die Propositions-Tabelle
  lab.py cards TABELLE.md [--topic T] [--out cards.json]   # Tabelle pruefen, Karten (Set 'lab') erzeugen
Quellen: Mollick (Assigning AI, 7 Arten), Lo (CLEAR: Concise, Logical, Explicit, Adaptive, Reflective).
"""
import argparse
import hashlib
import json
import sys

MAX_TEXT = 12000  # Eingabe-Deckel in Zeichen (Token-Sparsamkeit)
RELATIONS = ("ist ein Typ von", "wird verursacht durch", "erklärt")
LEVELS = {"child": "Kind", "highschool": "Oberstufe", "academic": "akademisch"}

TUTOR = """Du bist ein Sokratischer Tutor (CLEAR: knapp, logisch, explizit, anpassbar, reflektierend).
Thema: {topic}
Niveau: {level}
{source_rule}
Regeln:
1. Gib keine Antwort zuerst. Frag zuerst, was ich schon weiss, und lass mich einen eigenen Versuch machen.
2. Stell pro Nachricht genau eine Frage. Bei Fehlern gib einen Hinweis statt der Loesung.
3. Erst nach meinem Versuch erklaerst du, auf meinem Niveau, mit einer Analogie.
4. Wenn ich es richtig habe, erhoehe das Niveau (Kind, Oberstufe, akademisch).
5. Sag offen, wenn du unsicher bist. Aussagen sind belegt und nicht erfunden; Unsicheres markierst du mit [pruefen].
6. Stelle zum Schluss zwei Multiple-Choice-Szenariofragen im Stil der Pruefung (vier Optionen, eine Frage, Aufloesung erst nach meiner Antwort und meiner Sicherheitsangabe).
7. Am Ende: zwei Reflexionsfragen (Was war unsicher? Was hast du anders eingeschaetzt?).
Beginne jetzt mit Regel 1."""

MULTI = """Erklaere mir {topic} in drei Stufen, jeweils in hoechstens 4 Saetzen:
1. Kind (Analogie aus dem Alltag)
2. Oberstufe (Mechanismus, ein Beispiel)
3. akademisch (Fachbegriffe, Grenzen, offene Fragen)
Markiere Unsicheres mit [pruefen]. Stelle danach eine Kontrollfrage zur Stufe 2."""

PROPS = """Liste die Propositionen des folgenden Textes als Tabelle mit genau drei Spalten: X | Beziehung | Y.
Erlaubte Beziehungen, woertlich: "ist ein Typ von", "wird verursacht durch", "erklärt".
Nur Aussagen, die im Text stehen. Nichts ergaenzen. Kurze Begriffe, keine Saetze.
TEXT:
{text}"""


def tutor_prompt(topic, level="auto", source=None):
    if level != "auto" and level not in LEVELS:
        raise ValueError("level: auto|" + "|".join(LEVELS))
    lv = "frage mich zuerst nach meinem Stand" if level == "auto" else LEVELS[level]
    rule = ("Arbeite NUR mit dem folgenden Quelltext; Fragen ausserhalb davon lehnst du ab.\nQUELLE:\n"
            + source[:MAX_TEXT]) if source else "Ohne Quelltext: stuetze dich nur auf gesichertes Wissen."
    return TUTOR.format(topic=topic, level=lv, source_rule=rule)


def multilevel_prompt(topic):
    return MULTI.format(topic=topic)


def propositions_prompt(text):
    return PROPS.format(text=text[:MAX_TEXT])


def parse_table(md):
    """Markdown-Tabelle -> (Tripel ohne Duplikate, Probleme). Kopf- und Trennzeilen werden uebersprungen."""
    rows, problems, seen = [], [], set()
    for n, line in enumerate(md.splitlines(), 1):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: ") or cells[:3] == ["X", "Beziehung", "Y"]:
            continue
        if len(cells) != 3 or not all(cells):
            problems.append("Zeile %d: drei gefuellte Spalten erwartet" % n)
        elif cells[1] not in RELATIONS:
            problems.append("Zeile %d: unbekannte Beziehung '%s'" % (n, cells[1]))
        elif tuple(cells) not in seen:
            seen.add(tuple(cells))
            rows.append(tuple(cells))
    return rows, problems


def to_cards(rows, topic=""):
    cards = []
    for x, rel, y in rows:
        cid = "lab-" + hashlib.sha1(("%s|%s|%s" % (x, rel, y)).encode("utf-8")).hexdigest()[:10]
        cards.append({"id": cid, "set": "lab", "topic": topic, "front": "%s %s … ?" % (x, rel), "back": y})
    return cards


MODES = {"tutor": ("A", "den Sokratischen Tutor"), "multilevel": ("B", "die Multi-Level-Erklärung"),
         "props": ("C", "die Propositions-Tabelle")}
STRONG = 0.75   # ab hier kein Fokus mehr
MIN_EVIDENCE = 1.5


def pick(cands, n=4):
    """Kandidaten (id,text,m,n,gap,sure_wrong,refs) -> bis zu n Fokus-Eintraege mit Modus und Grund. Regeln:
    sicher & falsch -> Tutor (Fehlvorstellung aufdecken); kaum Evidenz -> Multi-Level; sonst schwach mit Evidenz -> Tutor.
    Propositionen (C) werden nicht automatisch gewaehlt: fuer eine Multiple-Choice-Pruefung nur optional (Owner-Entscheid 16.10.)."""
    out = []
    for c in cands:
        if c["m"] >= STRONG:
            continue
        if c["sure_wrong"]:
            mode, why = "tutor", "sicher & falsch (%d Frage%s), Hyperkorrektur" % (c["sure_wrong"], "" if c["sure_wrong"] == 1 else "n")
        elif c["n"] < MIN_EVIDENCE:
            mode, why = "multilevel", "kaum Evidenz (Beherrschung %d %%)" % round(100 * c["m"])
        else:
            mode, why = "tutor", "schwach trotz Evidenz (Beherrschung %d %%)" % round(100 * c["m"])
        out.append(dict(c, mode=mode, why=why))
    out.sort(key=lambda e: (-e["sure_wrong"], -e["gap"], e["id"]))
    return out[:n]


def render_focus(entries, today):
    lines = ["### Lab-Fokus (Schwachstellentraining) — " + today, "",
             "Automatisch aus dem Lern-Log gewaehlt. Nimm je Thema den genannten Basis-Prompt (A Tutor, B Multi-Level, C Propositionen) "
             "aus den Lab-Quellen und setze das Thema ein. Ergebnisse zaehlen nicht in die Reife-Messung; schliesse mit den zwei Reflexionsfragen.", ""]
    if not entries:
        lines.append("- Heute keine Schwachstellen im Fokus (alle Lernziele ueber %d %%)." % round(100 * STRONG))
        return "\n".join(lines)
    for i, e in enumerate(entries, 1):
        key, name = MODES[e["mode"]]
        refs = ["Rita Kap. %s (S. %s)" % (r["ch"], r["pages"]) for r in e["refs"].get("rita", [])[:2]]
        refs += ["PMBOK 8 " + r for r in e["refs"].get("pmbok8", [])[:2]]
        lines += ["%d. **%s %s** — %s" % (i, e["id"], e["text"], e["why"]),
                  "   - Modus: Basis-Prompt %s, %s" % (key, name),
                  "   - Quelle: " + ("; ".join(refs) or "—")]
    return "\n".join(lines)


def basis_prompts():
    """Die drei Basis-Prompts mit {THEMA}-Platzhalter, als Quelle fuer das Gemini-Notebook."""
    return "\n\n".join([
        "## A — Sokratischer Tutor\n" + tutor_prompt("{THEMA}"),
        "## B — Multi-Level-Erklärung\n" + multilevel_prompt("{THEMA}"),
        "## C — Propositionen\n" + PROPS.format(text="{THEMA}: hier den Quelltext einfuegen")]) + "\n"


def focus_section(today=None, n=4):
    """Liest den echten Lernstand (xlrte, Drive-Kopie) und baut den Fokus-Abschnitt. Aendert nichts."""
    import xlrte
    c = xlrte.cfg()
    today = today or xlrte.today_local()
    syl, eco, items, gloss = xlrte.load_content()
    events = xlrte.read_events()
    ev = xlrte.evidence(events, items, gloss, today, "pmp", eco, c)
    mm = xlrte.mastery_map(eco, ev, c)
    lw = xlrte.lo_weights(eco)
    it_lo = {it["id"]: it.get("lo") for it in items if it.get("exam") == "pmp"}
    last = {}
    for e in sorted((e for e in events if e["kind"] == "attempt" and e.get("exam") == "pmp" and e["ref"] in it_lo),
                    key=lambda e: e.get("ts", "")):
        x = last.setdefault(e["ref"], {})
        if (e["value"] or 0) >= 1:
            x["ok"] = e.get("ts", "")
        elif (e.get("meta") or {}).get("conf") == "sure":
            x["sw"] = e.get("ts", "")
    sw = {}
    for ref, x in last.items():
        if x.get("sw") and not (x.get("ok", "") > x["sw"]) and it_lo.get(ref):
            sw[it_lo[ref]] = sw.get(it_lo[ref], 0) + 1
    q = eco.get("questions", 40)
    cands = [dict(id=lo["id"], text=lo["text"], m=mm[lo["id"]]["m"], n=mm[lo["id"]]["n"],
                  gap=q * lw.get(lo["id"], 0) * (1 - mm[lo["id"]]["m"]), sure_wrong=sw.get(lo["id"], 0), refs=lo.get("refs", {}))
             for lo in eco.get("los", [])]
    return render_focus(pick(cands, n), today.isoformat())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tutor"); t.add_argument("topic"); t.add_argument("--level", default="auto"); t.add_argument("--source")
    m = sub.add_parser("multilevel"); m.add_argument("topic")
    p = sub.add_parser("props"); p.add_argument("file")
    f = sub.add_parser("focus"); f.add_argument("--n", type=int, default=4); f.add_argument("--out")
    sub.add_parser("basis")
    c = sub.add_parser("cards"); c.add_argument("file"); c.add_argument("--topic", default=""); c.add_argument("--out")
    a = ap.parse_args(argv)
    read = lambda f: open(f, encoding="utf-8").read()
    if a.cmd == "tutor":
        print(tutor_prompt(a.topic, a.level, read(a.source) if a.source else None))
    elif a.cmd == "multilevel":
        print(multilevel_prompt(a.topic))
    elif a.cmd == "basis":
        print(basis_prompts())
    elif a.cmd == "focus":
        md = focus_section(n=a.n)
        if a.out:
            open(a.out, "w", encoding="utf-8").write(md + "\n")
        else:
            print(md)
    elif a.cmd == "props":
        print(propositions_prompt(read(a.file)))
    else:
        rows, problems = parse_table(read(a.file))
        for pr in problems:
            print("WARN", pr, file=sys.stderr)
        out = json.dumps(to_cards(rows, a.topic), ensure_ascii=False, indent=1)
        if a.out:
            open(a.out, "w", encoding="utf-8").write(out)
        else:
            print(out)
        print("%d Karten, %d Probleme" % (len(rows), len(problems)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
