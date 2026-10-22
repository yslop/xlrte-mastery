"""Fallen-Radar Statistik (rein). Spiegel von trapStats() in templates/app.js; beide werden gegen tests/trap_stats_fixture.json geprüft."""
import datetime as dt

MIN_N = 5


def _day(s):
    return s if isinstance(s, dt.date) else dt.date.fromisoformat(str(s)[:10])


def _r4(x):
    return None if x is None else round(x, 4)


def visible_items(items, events):
    """Mock-Fragen zählen erst, wenn ihr Teil oder der Vollmock einmal gespielt wurde (wie mockSeen im Cockpit)."""
    refs = {e.get("ref") for e in events if e.get("kind") == "exam"}
    return [i for i in items if not i.get("mock") or ("XLRTE-" + i.get("set", "")) in refs or ("XLRTE-" + i["mock"]) in refs]


def trap_stats(events, items, traps, today, exam="pmp", half_life=10.0):
    today = _day(today)
    tags, lures = traps.get("items", {}), traps.get("lures", {})
    visible = {i["id"] for i in items if i.get("exam") == exam}
    acc = {t["id"]: dict(n=0, w=0.0, c=0.0, sw=0, rn=0, rc=0.0, pn=0, pc=0.0, wp=0, lp=0) for t in traps.get("taxonomy", [])}
    for e in events:
        if e.get("kind") != "attempt" or e.get("exam") != exam or e.get("ref") not in visible:
            continue
        ts = tags.get(e["ref"]) or []
        meta = e.get("meta") or {}
        age = max(0, (today - _day(e["date"])).days)
        val = float(e.get("value") or 0)
        c = (0.5 if meta.get("conf") == "guess" else 1.0) if val >= 1 else 0.0
        ww = 0.5 ** (age / half_life)
        pick = meta.get("pick")
        for t in ts:
            a = acc.get(t)
            if a is None:
                continue
            a["n"] += 1; a["w"] += ww; a["c"] += ww * c
            if val < 1 and meta.get("conf") == "sure":
                a["sw"] += 1
            if age <= 6:
                a["rn"] += 1; a["rc"] += c
            elif age <= 13:
                a["pn"] += 1; a["pc"] += c
            if val < 1 and pick is not None and e["ref"] in lures:
                a["wp"] += 1
                if lures[e["ref"]].get(str(pick)) == t:
                    a["lp"] += 1
    out = {}
    for t, a in acc.items():
        quote = a["c"] / a["w"] if a["w"] else None
        trend = (a["rc"] / a["rn"] - a["pc"] / a["pn"]) if a["rn"] >= MIN_N and a["pn"] >= MIN_N else None
        out[t] = {"n": a["n"], "quote": _r4(quote), "sure_wrong": a["sw"], "trend": _r4(trend),
                  "status": "ok" if a["n"] >= MIN_N else "zu wenig Daten",
                  "gap": _r4(a["w"] * (1 - quote)) if quote is not None else 0.0,
                  "lure_share": _r4(a["lp"] / a["wp"]) if a["wp"] else None}
    return out


def ranked(stats, taxonomy):
    """Daten-reiche Fallen nach Lücke absteigend, danach 'zu wenig Daten' nach Versuchen absteigend."""
    return sorted(taxonomy, key=lambda t: (0, -stats[t["id"]]["gap"]) if stats[t["id"]]["status"] == "ok" else (1, -stats[t["id"]]["n"]))


def profile_lines(stats, taxonomy):
    rows = []
    for t in ranked(stats, taxonomy):
        s = stats[t["id"]]
        if s["status"] != "ok":
            rows.append(f"- {t['name']}: zu wenig Daten ({s['n']} Versuche)")
            continue
        txt = f"- {t['name']}: {s['n']} Versuche · Quote {round(100 * s['quote'])} % · sicher & falsch {s['sure_wrong']}"
        if s["trend"] is not None:
            txt += f" · Trend {round(100 * s['trend']):+d} Pp"
        if s["lure_share"] is not None:
            txt += f" · verlockende Option gewählt {round(100 * s['lure_share'])} %"
        rows.append(txt)
    return ["### Fallen (PMP)", "", *rows, ""]
