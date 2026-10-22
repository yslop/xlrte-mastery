#!/usr/bin/env python3
"""Create a learning pack for any exam: packs/<id>/ with pack.json, items.json, glossary.json and a short guide.

    python3 scripts/new_pack.py --name "AWS Solutions Architect Associate" --short "AWS SAA" --lang en \
        --category "Secure architectures;30" --category "Resilient architectures;26" ... [--questions 65 --minutes 130 --pass 72]

Each category gets one starter objective (<cat>.1). Then add objectives, cards and questions (by hand, or with your own AI
from your own notes, see the guide in the pack). The daily run picks the pack up automatically; gen_drills.py makes new
practice questions from its cards every day. Never overwrites an existing pack.
"""
import argparse
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

GUIDE = """# {name}: Lernpaket

Dieses Paket gehört dir. Fülle es mit eigenen Formulierungen; kopiere keine Prüfungsfragen und keine Buch- oder Kurstexte.

| Datei | Inhalt |
|---|---|
| `pack.json` | Name, Sprache, Prüfungsformat, Kategorien mit Gewicht (Summe 100), Lernziele (`id`, `cat`, `text`) |
| `glossary.json` | Begriffskarten: `term`, `definition`, `los` (Lernziel-IDs). Aus ihnen entstehen täglich neue Übungsfragen |
| `items.json` | Eigene Fragen: `id`, `lo`, `q`, `options` (4), `answer` (Index), `why` |

**Mit deiner KI füllen** (lokal oder dein Abo), zum Beispiel:

> Lies meine Notizen in `<Ordner>`. Schlage für das Lernpaket `packs/{id}` Lernziele je Kategorie vor, dann je Lernziel drei
> Begriffskarten und zwei Prüfungsfragen mit vier Optionen und Begründung, in eigenen Worten. Schreibe nur in `glossary.json`
> und `items.json` dieses Pakets und zeige mir vorher die Liste.

Prüfen: `python3 _xlrte/scripts/xlrte.py check` · Neu bauen: `./mastery`.
"""


def slug(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "pack"


def create(name, short="", lang="de", categories=(), questions=40, minutes=60, pass_pct=65, pack_id=None):
    pid = pack_id or slug(short or name)
    d = os.path.join(ROOT, "packs", pid)
    if os.path.exists(os.path.join(d, "pack.json")):
        return {"id": pid, "created": False, "path": d}
    cats = []
    for i, c in enumerate(categories or [("Allgemein", 100)], 1):
        cname, weight = c if isinstance(c, (tuple, list)) else (c, 0)
        cats.append({"id": "K%d" % i, "name": cname.strip(), "weight": float(weight or 0)})
    if cats and not any(c["weight"] for c in cats):
        for c in cats:
            c["weight"] = round(100 / len(cats), 1)
    los = [{"id": "%s.1" % c["id"], "cat": c["id"], "text": c["name"]} for c in cats]
    pack = {"id": pid, "name": name, "short": short or name, "lang": lang, "version": "0.1", "license": "CC BY-SA 4.0",
            "exam": {"questions": int(questions), "minutes": int(minutes), "pass_pct": int(pass_pct)},
            "categories": cats, "los": los, "items": ["items.json"], "glossary": ["glossary.json"]}
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "pack.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
    for fn in ("items.json", "glossary.json"):
        with open(os.path.join(d, fn), "w", encoding="utf-8") as f:
            f.write("[]\n")
    with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
        f.write(GUIDE.format(name=name, id=pid))
    return {"id": pid, "created": True, "path": d}


def parse_category(text):
    name, _, w = text.partition(";")
    try:
        return name.strip(), float(w.strip().rstrip("%").replace(",", ".")) if w.strip() else 0
    except ValueError:
        return name.strip(), 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Create a learning pack for any exam")
    ap.add_argument("--name", required=True)
    ap.add_argument("--short", default="")
    ap.add_argument("--id")
    ap.add_argument("--lang", default="de", choices=["de", "en"])
    ap.add_argument("--category", action="append", default=[], help="'Name;Gewicht', repeat")
    ap.add_argument("--questions", type=int, default=40)
    ap.add_argument("--minutes", type=int, default=60)
    ap.add_argument("--pass", dest="pass_pct", type=int, default=65)
    a = ap.parse_args(argv)
    print(json.dumps(create(a.name, a.short, a.lang, [parse_category(c) for c in a.category], a.questions, a.minutes, a.pass_pct, a.id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
