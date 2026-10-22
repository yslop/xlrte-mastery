#!/usr/bin/env python3
"""XLRTE Lernsystem — engine for the ITIL 5 / PMP certification cockpit.

Stdlib only (Python >= 3.9). One fact, one place:
  state/events.csv        append-only event log (single source of truth for progress)
  data/*.json             content (syllabus, ECO, item banks, glossary, sources index)
  journal/*.json          event exports from the browser app -> merged here
  inbox/                  new materials / transcripts -> enrichment
Everything else (XLRTE_Cockpit.html, notebooklm/*.md, bridge/*) is DERIVED and may be regenerated.

Usage:
  python3 scripts/xlrte.py run [--today YYYY-MM-DD]        # full daily run (RUNBOOK_LERNTAG.md)
  python3 scripts/xlrte.py merge-journal | ingest-inbox | ingest-glossary --pdf P
  python3 scripts/xlrte.py status | briefing | render | check | bridge
"""
import argparse, csv, datetime as dt, glob, hashlib, json, math, os, re, shutil, subprocess, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trapstats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))          # .../_xlrte
OUTDIR = os.path.abspath(os.path.join(ROOT, ".."))        # .../Lernordner
P = lambda *a: os.path.join(ROOT, *a)
EVENT_COLS = ["id", "ts", "date", "kind", "exam", "ref", "value", "minutes", "meta"]


# ----------------------------------------------------------------------------- time (Zeitzone des Lerners)
TZ_NAME = os.environ.get("XLRTE_TZ", "Europe/Berlin")


def _berlin_offset_hours(utc):
    """Fallback ohne tzdata: MEZ (+1) / MESZ (+2); Sommerzeit von letztem Sonntag im März 01:00 UTC bis letztem Sonntag im Oktober 01:00 UTC."""
    def last_sunday(y, m):
        d = dt.datetime(y, m, 31 if m in (3, 10) else 30, 1)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    return 2 if last_sunday(utc.year, 3) <= utc < last_sunday(utc.year, 10) else 1


def now_local():
    """Aktuelle Uhrzeit des Lerners (Europe/Berlin) als naive datetime, unabhängig von der Prozess-Zeitzone (die Routine läuft in UTC)."""
    utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(TZ_NAME)).replace(tzinfo=None)
    except Exception:
        return utc + dt.timedelta(hours=_berlin_offset_hours(utc))


def today_local():
    return now_local().date()


# ----------------------------------------------------------------------------- io
def jload(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def jsave(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _is_true(v):
    return v is True or v == 1 or str(v).strip().lower() in ("true", "1")


def cfg():
    """config.json, overlaid with the cockpit settings '<exam>.target_date' and '<exam>.booked' (last event wins),
    exactly like examCfg() in the cockpit - so the profile, briefing and countdown follow what the owner set there."""
    c = jload(P("config.json"), {})
    for e in read_events():
        if e.get("kind") != "setting":
            continue
        ref = str(e.get("ref") or "")
        key, _, field = ref.partition(".")
        ex = (c.get("exams") or {}).get(key)
        if ex is None:
            continue
        if field == "target_date" and e.get("value") not in (None, ""):
            ex["target_date"] = str(e["value"])[:10]
        elif field == "booked" and e.get("value") not in (None, ""):
            ex["booked"] = _is_true(e["value"])
    return c


def read_events(include_void=False, include_pretest=False):
    path = P("state", "events.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        try:
            r["meta"] = json.loads(r.get("meta") or "{}")
        except ValueError:
            r["meta"] = {}
        r["value"] = _num(r.get("value"))
        r["minutes"] = _num(r.get("minutes")) or 0
    if not include_void:    # entwertete Fehleinträge (setting/void) bleiben im Log, zählen aber nirgends
        voided = {str(r["value"]) for r in rows if r.get("kind") == "setting" and r.get("ref") == "void"}
        rows = [r for r in rows if r["id"] not in voided]
    if not include_pretest:   # Vorab-Test (Pretesting): Fehler sind gewollt, sie zählen nicht für Prognose, Wiederholung und Fehler-Management
        rows = [r for r in rows if not (r.get("kind") == "attempt" and (r.get("meta") or {}).get("mode") == "vorab")]
    return rows


def append_events(evs):
    path = P("state", "events.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EVENT_COLS)
        if new:
            w.writeheader()
        for e in evs:
            row = {k: e.get(k, "") for k in EVENT_COLS}
            row["meta"] = json.dumps(e.get("meta") or {}, ensure_ascii=False)
            w.writerow(row)


def _num(v):
    if v in (None, ""):
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return v


def new_event(kind, date, exam="", ref="", value="", minutes="", meta=None):
    return {"id": "e_" + uuid.uuid4().hex[:12], "ts": now_local().isoformat(timespec="seconds"),
            "date": date, "kind": kind, "exam": exam, "ref": ref, "value": value, "minutes": minutes,
            "meta": meta or {}}


def parse_day(s):
    return dt.date.fromisoformat(s[:10])


# ----------------------------------------------------------------------------- content
def load_content():
    syl = jload(P("data", "syllabus_itil5.json"), {})
    eco = jload(P("data", "eco_pmp2026.json"), {})
    items = []
    for f in ("items_itil5.json", "items_itil5_s1.json", "items_itil5_s2.json", "items_itil5_s3.json", "items_itil5_s4.json", "items_itil5_sp1.json", "items_itil5_sp2.json", "items_pmp.json", "items_pmp_mock1.json", "items_pmp_mock2.json", "items_pmp_mock3.json", "items_pmp_sz1.json", "items_pmp_sz2.json", "items_pmp_m2b.json", "items_pmp_m2c.json", "items_pmp_mb.json", "items_pmp_tr.json", "items_pmp_calc.json", "items_pmp_wm.json", "items_candidates.json"):
        items += jload(P("data", f), []) or []
    items += jload(P("data", "items_gen.json"), []) or []          # deterministic daily drills (gen_drills.py)
    for pid, (bank, p_items, p_gloss) in load_packs().items():
        items += [dict(it, exam=it.get("exam") or pid) for it in p_items]
    gloss = []
    for f, ex in (("glossary_itil5.json", "itil5"), ("glossary_pmp.json", "pmp"), ("glossary_pmp_pmi.json", "pmp"), ("glossary_pmp_ethik.json", "pmp"), ("glossary_pmp_ki.json", "pmp")):
        for g in jload(P("data", f), []) or []:
            g.setdefault("exam", ex)
            gloss.append(g)
    for pid, (bank, p_items, p_gloss) in load_packs().items():
        gloss += [dict(g, exam=g.get("exam") or pid) for g in p_gloss]
    import glossary_hints
    glossary_hints.attach([g for g in gloss if g.get("exam") == "pmp"])
    return syl, eco, items, gloss


def load_packs():
    """Learning packs for any exam: packs/<id>/pack.json -> {id: (bank, items, glossary)}.
    pack.json: {id, name, short?, lang, exam: {questions, minutes, pass_pct}, categories: [{id, name, weight}],
    los: [{id, cat, text}], items: ["items.json"], glossary: ["glossary.json"]}. A broken pack is skipped, never fatal."""
    out = {}
    for pj in sorted(glob.glob(P("packs", "*", "pack.json"))):
        p = jload(pj, None)
        if not isinstance(p, dict):
            continue
        d = os.path.dirname(pj)
        pid = str(p.get("id") or os.path.basename(d))
        ex = p.get("exam") or {}
        bank = {"id": pid, "name": p.get("name", pid), "short": p.get("short", ""), "lang": p.get("lang", "de"), "pack": True,
                "questions": ex.get("questions", 40), "minutes": ex.get("minutes", 60), "pass_pct": ex.get("pass_pct", 65),
                "categories": p.get("categories", []), "los": p.get("los", [])}
        its = [i for f in p.get("items", ["items.json"]) for i in (jload(os.path.join(d, f), []) or [])]
        gl = [g for f in p.get("glossary", ["glossary.json"]) for g in (jload(os.path.join(d, f), []) or [])]
        out[pid] = (bank, its, gl)
    return out


def load_banks():
    """Every exam with a blueprint: legacy ITIL/PMP files plus packs. -> {exam_key: bank}"""
    syl, eco, _, _ = load_content()
    banks = {}
    if syl.get("los"):
        banks["itil5"] = syl
    if eco.get("los"):
        banks["pmp"] = eco
    for pid, (bank, _, _) in load_packs().items():
        banks[pid] = bank
    return banks


def load_cases():
    return (jload(P("data", "cases_pmp.json"), []) or []) + [c for f in sorted(glob.glob(P("data", "cases_pmp_sz*.json")) + glob.glob(P("data", "cases_pmp_m2*.json"))) for c in (jload(f, []) or [])]


def lo_weights(bank):
    """Expected exam points per learning objective: category weight spread evenly over its LOs."""
    by_cat = {}
    for lo in bank.get("los", []):
        by_cat.setdefault(lo["cat"], []).append(lo["id"])
    w = {}
    for c in bank.get("categories", []):
        ids = by_cat.get(c["id"], [])
        for i in ids:
            w[i] = c["weight"] / 100.0 / len(ids)
    return w


# ----------------------------------------------------------------------------- model
EXT_DEFAULT = {"W_TASK": 1.0, "W_DOMAIN": 0.3, "mini": 0.8}


def ext_voided(events):
    return {e.get("ref") for e in events if e.get("kind") == "ext_void"}


def ext_valid(events, exam="pmp"):
    """Study-Hall-Ergebnisse (kind ext, nur Zahlen), ohne entwertete. Spiegel im Cockpit: shEvidence (app.js)."""
    void = ext_voided(events)
    return [e for e in events if e.get("kind") == "ext" and e.get("exam") == exam and e.get("id") not in void and (e.get("meta") or {}).get("src") == "studyhall"]


def ext_evidence(events, bank, today, exam, c):
    """-> [(lo_id, age, correct, weight)]: je Task n × W_TASK; nur Domäne: n × W_DOMAIN gleichmäßig auf die Tasks der Domäne (lo_weights sind je Kategorie gleich); Gesamtwert allein = kein Beleg."""
    W = {**EXT_DEFAULT, **(c.get("mastery", {}).get("ext") or {})}
    ids = {lo["id"] for lo in bank.get("los", [])}
    by_cat = {}
    for lo in bank.get("los", []):
        by_cat.setdefault(lo["cat"], []).append(lo["id"])
    out = []
    for e in ext_valid(events, exam):
        if parse_day(e["date"]) > today:
            continue
        m = e.get("meta") or {}
        f = W["mini"] if m.get("type") == "mini" else 1.0
        age = max(0, (today - parse_day(e["date"])).days)
        bt = {t: v for t, v in (m.get("by_task") or {}).items() if t in ids and v[1] > 0}
        if bt:
            out += [(t, age, v[0] / v[1], v[1] * W["W_TASK"] * f) for t, v in bt.items()]
        else:
            for d, v in (m.get("by_domain") or {}).items():
                lst = by_cat.get(d, [])
                if lst and v[1] > 0:
                    out += [(t, age, v[0] / v[1], v[1] * W["W_DOMAIN"] * f / len(lst)) for t in lst]
    return out


def studyhall_summary(events, bank, today, c, exam="pmp"):
    """Zahlen zu Study Hall für Briefing, Lernprofil und Lauf-Bericht: Einträge, letzte Full-Length, Belege je Task (nur Zahlen, nie Inhalte)."""
    ex = ext_valid(events, exam)
    full = sorted((e for e in ex if str(e.get("ref", "")).startswith("SH-FULL")), key=lambda e: (e["date"], e.get("ts", "")))
    by_task = {}
    for lo, *_ in ext_evidence(events, bank, today, exam, c):
        by_task[lo] = by_task.get(lo, 0) + 1
    last = full[-1] if full else None
    return {"entries": len(ex), "last_full": (f"{last['ref'].replace('SH-', '')} {int(last['value'] or 0)}/{(last.get('meta') or {}).get('of', 180)} am {last['date']}" if last else None), "by_task": by_task}


def studyhall_day(events, day, exam="pmp"):
    """Study-Hall-Einträge eines Tages als kurze Textzeilen (nur Zahlen)."""
    out = []
    for e in ext_valid(events, exam):
        if e["date"] == day.isoformat():
            m = e.get("meta") or {}
            out.append(f"{e['ref']} {int(e['value'] or 0)}/{m.get('of', '?')}")
    return out


def evidence(events, items, gloss, today, exam, bank=None, c_cfg=None):
    """-> {lo_id: [(age_days, correct(0..1), weight)]} from attempts + card reviews (+ Study-Hall-Belege, wenn bank und c übergeben)."""
    item_lo = {it["id"]: it.get("lo") for it in items if it.get("exam") == exam and not it.get("drill")}   # Trainer-Drill: kein Mastery-Beleg (Task-Zuordnung per Stichwort)
    card_lo = {g["id"]: g.get("los", []) for g in gloss if g.get("exam", "itil5") == exam}
    ev = {}
    for e in events:
        if e.get("exam") != exam:
            continue
        age = max(0, (today - parse_day(e["date"])).days)
        if e["kind"] == "attempt" and e["ref"] in item_lo and item_lo[e["ref"]]:
            conf = (e.get("meta") or {}).get("conf", "sure")
            c = float(e["value"] or 0)
            if c >= 1 and conf == "guess":
                c = 0.5
            ev.setdefault(item_lo[e["ref"]], []).append((age, c, 1.0))
        elif e["kind"] == "card" and e["ref"] in card_lo:
            c = 1.0 if (e["value"] or 0) >= 2 else 0.0
            for lo in card_lo[e["ref"]]:
                ev.setdefault(lo, []).append((age, c, 0.5))
    if bank is not None and exam == "pmp":
        for lo, age, corr, w in ext_evidence(events, bank, today, exam, c_cfg):
            ev.setdefault(lo, []).append((age, corr, w))
    return ev


def mastery_map(bank, ev, c):
    hl = c.get("mastery", {}).get("half_life_days", 10)
    a0 = c.get("mastery", {}).get("prior_a", 0.5)
    b0 = c.get("mastery", {}).get("prior_b", 1.5)
    out = {}
    for lo in bank.get("los", []):
        s_w = s_c = 0.0
        for age, corr, w in ev.get(lo["id"], []):
            ww = w * (0.5 ** (age / hl))
            s_w += ww
            s_c += ww * corr
        out[lo["id"]] = {"m": (a0 + s_c) / (a0 + b0 + s_w), "n": round(s_w, 2)}
    return out


def readiness(bank, mm, c, exam_key):
    ex = c.get("exams", {}).get(exam_key, {})
    total_q = bank.get("questions", 40)
    by_cat = {}
    for lo in bank.get("los", []):
        by_cat.setdefault(lo["cat"], []).append(mm[lo["id"]])
    cats, pred, cov_w = [], 0.0, 0.0
    lw = lo_weights(bank)
    for cat in bank.get("categories", []):
        lst = by_cat.get(cat["id"], [])
        m = sum(x["m"] for x in lst) / len(lst) if lst else 0.25
        q = total_q * cat["weight"] / 100.0
        pred += q * m
        cats.append({"id": cat["id"], "name": cat["name"], "weight": cat["weight"], "mastery": round(m, 3),
                     "expected_points": round(q * m, 1), "questions": round(q, 1)})
    for lo in bank.get("los", []):
        if mm[lo["id"]]["n"] >= 1.5:
            cov_w += lw.get(lo["id"], 0)
    p = pred / total_q
    unc = (6.0 * (1 - cov_w) + 1.5) * (total_q / 40.0)     # same scaling as the cockpit (app.js)
    sd = math.sqrt(total_q * p * (1 - p) + unc ** 2)
    need = total_q * ex.get("pass_pct", 65) / 100.0 - 0.5
    p_pass = 0.5 * (1 + math.erf((pred - need) / (sd * math.sqrt(2))))
    return {"predicted": round(pred, 1), "of": total_q, "pct": round(100 * p, 1), "coverage": round(100 * cov_w, 1),
            "p_pass": round(p_pass, 3), "categories": cats}


def weak_los(bank, mm, n=5):
    lw = lo_weights(bank)
    ranked = sorted(bank.get("los", []), key=lambda lo: -lw.get(lo["id"], 0) * (1 - mm[lo["id"]]["m"]))
    return [{"id": lo["id"], "text": lo["text"], "book": lo.get("book", ""), "m": round(mm[lo["id"]]["m"], 2),
             "gap_points": round(bank.get("questions", 40) * lw.get(lo["id"], 0) * (1 - mm[lo["id"]]["m"]), 2)}
            for lo in ranked[:n]]


def srs_state(events, c):
    """Leitner replay -> {ref: {box, last, due}} for attempts & cards."""
    iv = c.get("srs_intervals_days", [0, 1, 2, 4, 8, 16])
    st = {}
    for e in sorted(events, key=lambda x: x.get("ts", "")):
        if e["kind"] not in ("attempt", "card"):
            continue
        s = st.setdefault(e["ref"], {"box": 0, "last": e["date"]})
        good = (e["value"] or 0) >= (2 if e["kind"] == "card" else 1)
        guess = (e.get("meta") or {}).get("conf") == "guess"
        if good and not guess:
            s["box"] = min(len(iv) - 1, s["box"] + 1)
        elif not good:
            s["box"] = 1
        s["last"] = e["date"]
        s["due"] = (parse_day(e["date"]) + dt.timedelta(days=iv[s["box"]])).isoformat()
    return st


def day_stats(events, day):
    d = day.isoformat()
    todays = [e for e in events if e["date"] == d]
    att = [e for e in todays if e["kind"] == "attempt"]
    cards = [e for e in todays if e["kind"] == "card"]
    focus = sum(e["minutes"] or 0 for e in todays if e["kind"] in ("focus", "activity"))
    corr = sum(1 for e in att if (e["value"] or 0) >= 1)
    return {"attempts": len(att), "correct": corr, "cards": len(cards), "focus_minutes": focus,
            "retrievals": len(att) + len(cards), "activities": [e for e in todays if e["kind"] == "activity"]}


def streak(events, today, c):
    need = c.get("streak_min", {"retrievals": 25, "focus_minutes": 60})
    s, d = 0, today
    for _ in range(120):
        if d.weekday() >= 5:            # weekends never break a streak (rest is part of the system)
            d -= dt.timedelta(days=1)
            continue
        st = day_stats(events, d)
        ok = st["retrievals"] >= need["retrievals"] or (st["focus_minutes"] >= need["focus_minutes"] and st["retrievals"] >= 10)
        if ok:
            s += 1
        elif d != today:
            break
        d -= dt.timedelta(days=1)
    return s


def current_phase(c, today):
    for ph in c.get("phases", []):
        if parse_day(ph["from"]) <= today <= parse_day(ph["to"]):
            return ph
    upcoming = [ph for ph in c.get("phases", []) if parse_day(ph["from"]) > today]
    return upcoming[0] if upcoming else None


def workdays(a, b):
    n, d = 0, a
    while d <= b:
        if d.weekday() < 5:
            n += 1
        d += dt.timedelta(days=1)
    return n


def evm(bank, mm, events, c, exam_key, today):
    """The learning plan run as a project: PMI Earned Value on hours."""
    ex = c["exams"][exam_key]
    start, end = parse_day(ex["plan_start"]), parse_day(ex["target_date"])
    bac = float(ex.get("plan_hours", 40))
    tot = max(1, workdays(start, end))
    done = workdays(start, min(today, end)) if today >= start else 0
    pv = bac * done / tot
    lw = lo_weights(bank)
    solid = c.get("mastery", {}).get("solid", 0.8)
    m0 = c.get("mastery", {}).get("prior_a", 0.5) / (c.get("mastery", {}).get("prior_a", 0.5) + c.get("mastery", {}).get("prior_b", 1.5))
    ev_frac = sum(lw.get(i, 0) * max(0.0, min(1.0, (v["m"] - m0) / (solid - m0))) for i, v in mm.items())
    ev = bac * ev_frac
    ac = sum((e["minutes"] or 0) for e in events if e.get("exam") == exam_key and e["kind"] in ("focus", "activity")) / 60.0
    cpi = ev / ac if ac > 0 else None
    spi = ev / pv if pv > 0 else None
    return {"bac": round(bac, 1), "pv": round(pv, 1), "ev": round(ev, 1), "ac": round(ac, 1),
            "cpi": round(cpi, 2) if cpi else None, "spi": round(spi, 2) if spi else None,
            "eac": round(bac / cpi, 1) if cpi else None, "sv": round(ev - pv, 1), "cv": round(ev - ac, 1) if ac else None}


def compute(today=None):
    c = cfg()
    today = today or today_local()
    syl, eco, items, gloss = load_content()
    events = read_events()
    out = {"today": today.isoformat(), "phase": current_phase(c, today), "streak": streak(events, today, c)}
    for key, bank in load_banks().items():
        if key not in (c.get("exams") or {}):
            continue
        ev = evidence(events, items, gloss, today, key, bank, c)
        mm = mastery_map(bank, ev, c)
        out[key] = {"readiness": readiness(bank, mm, c, key), "weak": weak_los(bank, mm), "evm": evm(bank, mm, events, c, key, today),
                    "mastery": {k: round(v["m"], 3) for k, v in mm.items()}}
    srs = srs_state(events, c)
    due = [r for r, s in srs.items() if s.get("due", "9999") <= today.isoformat()]
    out["srs_due"] = len(due)
    out["yesterday"] = day_stats(events, today - dt.timedelta(days=1 if today.weekday() != 0 else 3))
    out["today_stats"] = day_stats(events, today)
    return out


# ----------------------------------------------------------------------------- journal merge
def _local_date(ts):
    """Cockpit stores ts in UTC (toISOString); date must be the learner's local day (Europe/Berlin)."""
    try:
        from zoneinfo import ZoneInfo
        t = dt.datetime.fromisoformat(str(ts)[:19]).replace(tzinfo=dt.timezone.utc)
        return t.astimezone(ZoneInfo("Europe/Berlin")).date().isoformat()
    except Exception:
        return None


def merge_journal():
    """Merge cockpit exports. Robust since 26.09.2026:
    - 0-byte / unparsable files are moved to journal/_defekt/ (never deleted, never re-reported every day);
      the cockpit keeps those events pending and re-exports them, so no data is lost.
    - files younger than 2 min are left alone (export may still be in progress).
    - Chrome swap files (*.crswap) with valid JSON are recovered.
    - event date is re-derived from ts when a stale tab stamped yesterday's date."""
    known = {e["id"] for e in read_events(include_void=True, include_pretest=True)}
    files = sorted(glob.glob(P("journal", "*.json")) + glob.glob(P("journal", "*.crswap")))
    added, merged_files, broken = [], [], []
    empty = invalid = recent = date_fixed = 0
    now = dt.datetime.now().timestamp()
    for f in files:
        try:
            size, age = os.path.getsize(f), now - os.path.getmtime(f)
        except OSError:
            continue
        if age < 120:
            recent += 1
            continue
        if size == 0:
            empty += 1
            broken.append(f)
            continue
        data = jload(f, None)
        if data is None:
            invalid += 1
            broken.append(f)
            print(f"UNKLAR: {os.path.basename(f)} ist kein gültiges JSON ({size} Bytes) – nach journal/_defekt/ verschoben")
            continue
        evs = data.get("events", data) if isinstance(data, dict) else data
        for e in evs:
            if not isinstance(e, dict) or not e.get("id") or e["id"] in known:
                continue
            if e.get("kind") not in ("attempt", "card", "activity", "focus", "attendance", "recap", "exam", "workaround",
                                     "review", "setting", "note"):
                continue
            ld = _local_date(e.get("ts", ""))
            if ld and e.get("date") != ld:
                e["date"] = ld
                date_fixed += 1
            known.add(e["id"])
            added.append(e)
        merged_files.append(f)
    if added:
        append_events(sorted(added, key=lambda x: x.get("ts", "")))
    os.makedirs(P("journal", "_merged"), exist_ok=True)
    for f in merged_files:                      # organise, never delete
        shutil.move(f, P("journal", "_merged", os.path.basename(f)))
    if broken:
        os.makedirs(P("journal", "_defekt"), exist_ok=True)
        for f in broken:
            dst = P("journal", "_defekt", os.path.basename(f))
            if os.path.exists(dst):
                dst += "." + uuid.uuid4().hex[:6]
            shutil.move(f, dst)
    if empty:
        print(f"HINWEIS: {empty} leere Journal-Exporte (0 Bytes, abgebrochener Schreibvorgang) nach journal/_defekt/ verschoben – "
              f"Events bleiben im Cockpit ausstehend und kommen mit dem nächsten geprüften Export.")
    return {"files": len(merged_files), "events_added": len(added), "empty": empty, "invalid": invalid,
            "in_progress": recent, "date_fixed": date_fixed}


# ----------------------------------------------------------------------------- glossary
def ingest_glossary(pdf):
    try:
        import pypdf
    except ImportError:
        print("pypdf fehlt – Glossar-Import übersprungen (pip install pypdf)")
        return 0
    r = pypdf.PdfReader(pdf)
    entries, cur = [], None
    for page in r.pages:
        runs = []
        page.extract_text(visitor_text=lambda t, cm, tm, fd, fs: runs.append(((fd or {}).get("/BaseFont", ""), t)))
        for font, text in runs:
            t = text.strip()
            if not t or len(t) == 1:
                continue
            bold = "Bold" in str(font)
            if bold:
                if cur and cur["definition"]:
                    entries.append(cur)
                    cur = None
                if cur is None:
                    cur = {"term": t, "definition": ""}
                else:
                    cur["term"] += " " + t
            elif cur is not None:
                cur["definition"] += (" " if cur["definition"] else "") + t
    if cur and cur["definition"]:
        entries.append(cur)
    syl = jload(P("data", "syllabus_itil5.json"), {})
    out = []
    for i, e in enumerate(entries):
        wm = r"PeopleCert\s*Copyright\s*\S*\s*\d{4}\s*View\s*only\s*-?\s*Not\s*for\s*redistribution"
        term = re.sub(r"\s+", " ", re.sub(wm, " ", e["term"])).replace(" -", "-").replace("- ", "-").strip()
        definition = re.sub(r"\s+", " ", re.sub(wm, " ", e["definition"])).replace(" -", "-").strip()
        if len(definition) < 12 or term in ("Glossar",) or term.startswith("Für alle Organisationen"):
            continue
        out.append({"id": "g_" + hashlib.sha1(term.encode()).hexdigest()[:8], "term": term, "definition": definition,
                    "los": map_term_to_los(term, syl)})
    jsave(P("data", "glossary_itil5.json"), out)
    return len(out)


TERM_LO = {  # explicit anchors where the LO text does not literally contain the glossary term
    "Service": ["1.1.2"], "Produkt": ["1.1.2"], "Digitales Produkt": ["1.1.3"], "Digitaler Service": ["1.1.3"],
    "Waren": ["1.1.6"], "Utility": ["1.1.7", "1.4.11"], "Warranty": ["1.1.7", "1.4.11"], "Nachhaltigkeit": ["1.1.7"],
    "User Experience (UX)": ["1.1.7"], "Serviceangebot": ["1.2.1", "1.2.3"], "Serviceaktion": ["1.2.2"],
    "Wert": ["1.3.1"], "Gemeinsame Wertschaffung": ["1.3.1"], "Kosten": ["1.3.2"], "Risiko": ["1.3.2"],
    "Output": ["1.3.3", "1.3.4"], "Ergebnis": ["1.3.3", "1.3.4"], "Organisation": ["1.4.1"],
    "Service Provider": ["1.4.1", "1.4.7"], "Servicekonsument": ["1.4.1", "1.4.8"], "Anbieter digitaler Produkte": ["1.4.1", "1.4.9"],
    "Service Journey": ["1.4.3"], "Sponsor": ["1.4.4"], "Kunde": ["1.4.4"], "Anwender": ["1.4.4"],
    "Servicequalität": ["1.4.5"], "Service Level": ["1.4.5"], "Service Level Agreement (SLA)": ["1.4.6"],
    "Governance": ["4.3.1"], "Wertschöpfungskette": ["4.4.1"], "Incident": ["4.4.3"], "Event": ["4.4.3"],
    "Release": ["4.4.4"], "Testing": ["4.4.4"], "Continuous Integration": ["4.4.5"], "Continuous Delivery": ["4.4.5"],
    "Continuous Deployment": ["4.4.5"], "Zuverlässigkeit": ["4.4.6"], "Site Reliability Engineering (SRE)": ["4.4.6"],
    "Observability": ["4.4.6"], "Service Request": ["4.4.7"], "Katastrophe": ["4.4.8"], "Problem": ["4.4.8", "4.4.10"],
    "Fehler": ["4.4.8", "4.4.10"], "Known Error": ["4.4.8", "4.4.10"], "Betriebsmodell": ["4.4.9", "4.4.12"],
    "Management-Practice": ["4.5.1"], "Messgröße": ["4.5.6"], "Kritischer Erfolgsfaktor (Critical Success Factor, CSF)": ["4.5.6"],
    "Continual Improvement": ["1.1.4", "4.6.3"], "Wertstrom": ["5.1.1"], "Hauptwertstrom": ["5.1.1", "5.1.4"], "Kern-Wertstrom": ["5.1.1", "5.1.4"],
    "Unterstützender Wertstrom": ["5.1.1", "5.1.4"], "Wertstromdarstellung": ["5.1.2", "5.3.2"], "Wertstrommanagement": ["5.1.2", "5.3.2"],
    "Komplexitätsdenken": ["5.1.3", "5.2.1"], "Künstliche Intelligenz (KI)": ["6.1.1"], "KI-Reife": ["6.1.1"],
    "Generative KI (GenAI)": ["6.1.1"], "Agentische KI": ["6.1.1"], "Governance von KI": ["6.2.1"], "KI-Governance": ["6.2.1"],
    "ITIL Value System (ITIL VS)": ["4.1.1", "4.1.2"], "Das Management digitaler Produkte und Services": ["1.1.1"],
    "Produkt- und Servicelebenszyklus": ["1.1.5"], "Grundprinzip": ["4.2.1"], "Produkt-/Servicespezifikation": ["4.4.2"],
    "Produkt-/Serviceprototyp": ["4.4.2"], "Produktspezifikation": ["4.4.2"], "Produktprototyp": ["4.4.2"],
}


def _norm(s):
    return re.sub(r"[^a-zäöüß0-9 ]", " ", s.lower())


def map_term_to_los(term, syl):
    if term in TERM_LO:
        return TERM_LO[term]
    base = re.sub(r"\s*\(.*?\)", "", term).strip()
    for k, v in TERM_LO.items():
        if base.lower() == re.sub(r"\s*\(.*?\)", "", k).strip().lower():
            return v
    hits = []
    nb = _norm(base).strip()
    if len(nb) < 4:
        return []
    for lo in syl.get("los", []):
        if re.search(r"\b" + re.escape(nb) + r"\b", _norm(lo["text"])):
            hits.append(lo["id"])
    return hits[:3]


# ----------------------------------------------------------------------------- inbox enrichment
def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".csv", ".vtt", ".srt"):
        return open(path, encoding="utf-8", errors="ignore").read()
    if ext == ".pdf":
        try:
            return subprocess.run(["pdftotext", "-raw", path, "-"], capture_output=True, text=True, timeout=120).stdout
        except (OSError, subprocess.SubprocessError):
            try:
                import pypdf
                return "\n".join((pg.extract_text() or "") for pg in pypdf.PdfReader(path).pages)
            except Exception:
                return ""
    if ext == ".docx":
        import zipfile
        try:
            xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "ignore")
            return re.sub(r"<[^>]+>", " ", xml.replace("</w:p>", "\n"))
        except Exception:
            return ""
    return ""


def clean_text(text):
    text = re.sub(r"(?:(?<=\s)|^)(?:\S[ \n]){8,}\S(?=\s|$)", " ", text)          # spaced-out watermark letters
    text = re.sub(r"PeopleCert\s*Copyright\s*\S*\s*\d{4}\s*View\s*only\s*-?\s*Not\s*for\s*redistribution", " ", text)
    return text


def chunks(text, size=1400):
    text = re.sub(r"[ \t]+", " ", clean_text(text))
    raw = [p.strip() for p in re.split(r"\n\s*\n|\n(?=\d\d:\d\d:\d\d)", text) if p.strip()]
    paras = []
    for p in raw:                       # hard-split long blocks (e.g. pdftotext -raw without blank lines)
        while len(p) > size:
            cut = max(p.rfind("\n", 0, size), p.rfind(". ", 0, size))
            cut = cut if cut > size // 3 else size
            paras.append(p[:cut + 1].strip())
            p = p[cut + 1:]
        if p.strip():
            paras.append(p.strip())
    buf, out = "", []
    for p in paras:
        if len(buf) + len(p) > size and buf:
            out.append(buf)
            buf = ""
        buf += (" " if buf else "") + p
    if buf:
        out.append(buf)
    return out


GENERIC = set("""itil service services produkt produkte produkten digitaler digitale digitalen digitales management managements
organisation organisationen aktivität aktivitäten konzept konzepte zentrales zentrale schlüsselkonzept schlüsselkonzepte rolle rollen
verstehen definieren kennen erläutern erklären auflisten beschreiben anwenden angewendet sowie wissen sollte werden grundprinzip
lebenszyklus servicemanagements eines einer einem zwischen unterschied bedeutung project projects manage plan develop help ensure
team teams their within ihre ihren dass noch weder sind können kann wird werden wurde nicht auch alle allen aller durch über unter
sich diese dieser dieses jede jeder jedes oder sowohl einen einem ihrer seine seinen welche welcher wenn dann haben hat sein ohne
mehr sehr immer bereits dabei damit dazu darauf hierbei genutzt verwendet unterstützt unterstützen gemeinsam""".split())
WEAK_TERMS = {"service", "produkt", "wert", "organisation", "kunde", "anwender", "kosten", "risiko", "output", "ergebnis", "change",
              "event", "fehler", "problem", "release", "feedback", "kultur", "vision", "mission", "stakeholder"}


def keyword_index(syl, eco, gloss):
    stop = set("und oder der die das ein eine den dem des von zu im in als für mit wie was the and of to a an for".split()) | GENERIC
    stop |= set("this that with from into which what when should project projects manager team help ensure based needs throughout".split())
    idx = {}
    for lo in syl.get("los", []):
        kws = {w for w in _norm(lo["text"]).split() if len(w) > 3 and w not in stop}
        idx[("itil5", lo["id"])] = {k: 1.0 for k in kws}
    for g in gloss:
        t = _norm(re.sub(r"\(.*?\)", "", g["term"])).strip()
        if len(t) < 4:
            continue
        los = g.get("los", [])
        w = (0.8 if t in WEAK_TERMS else 2.5) / max(1, len(los)) ** 0.5
        for lo in los:
            idx.setdefault((g.get("exam", "itil5"), lo), {})[t] = w
    for t in eco.get("los", []):
        txt = " ".join([t["text"], t.get("focus", "")] + [e["text"] for e in t.get("enablers", [])])
        kws = {w: 1.0 for w in _norm(txt).split() if len(w) > 3 and w not in stop}
        for k in t.get("keywords", []):
            kws[_norm(k).strip()] = 2.5
        for k, w in kws.items():                               # merge: keep glossary terms indexed above
            cur = idx.setdefault(("pmp", t["id"]), {})
            cur[k] = max(w, cur.get(k, 0))
    return idx


def score_chunk(ch, idx):
    """-> [(score, key, strong_hits)] — strong = distinct glossary terms / 2+ LO keywords actually present."""
    n = " " + _norm(ch) + " "
    sc = []
    for key, kws in idx.items():
        s, strong = 0.0, 0
        for k, w in kws.items():
            c = n.count(" " + k + " ")
            if c:
                s += w * min(3, c)
                strong += 1 if w >= 1.0 else 0
        if s:
            sc.append((s / (1 + 0.1 * len(kws)), key, strong))
    sc.sort(reverse=True)
    return sc


def typesafe_key():
    k = os.environ.get("TYPESAFE_API_KEY", "")
    if k:
        return k
    for cand in (P(".env")):
        try:
            for line in open(cand, encoding="utf-8"):
                if line.strip().startswith("TYPESAFE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass
    return ""


def typesafe_choice(state, criteria, instructions, c):
    import urllib.request
    key = typesafe_key()
    if not key:
        return {"error": "TYPESAFE_API_KEY not set"}
    ts = c.get("typesafe", {})
    body = json.dumps({"state": state[:1500], "model": ts.get("model", "jev-latest"),
                       "questions": {"lo": {"type": "choice", "instructions": instructions, "criteria": criteria}}}).encode()
    req = urllib.request.Request(ts.get("url", "https://api.typesafe.ai/v1/systemone"), data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            a = json.loads(r.read())["answers"]["lo"]
            return {"choice": a["choice"], "confidence": a["confidence"]}
    except Exception as exc:  # fail open, never guess
        return {"error": str(exc)[:200]}


def candidate_keys(sc, n=5):
    """Top-n learning-objective keys from score_chunk() results, which are (score, key, strong) triples."""
    return [t[1] for t in sc[:n]]


def ingest_inbox(today):
    c = cfg()
    syl, eco, items, gloss = load_content()
    reg_path = P("state", "sources.csv")
    reg = {}
    if os.path.exists(reg_path):
        with open(reg_path, newline="", encoding="utf-8") as f:
            reg = {r["sha1"]: r for r in csv.DictReader(f)}
    index = jload(P("data", "sources_index.json"), {"sources": [], "by_lo": {}})
    idx = keyword_index(syl, eco, gloss)
    lo_text = {("itil5", lo["id"]): lo["text"] for lo in syl.get("los", [])}
    lo_text.update({("pmp", t["id"]): t["text"] + " — " + t.get("focus", "") for t in eco.get("los", [])})
    stats = {"files": 0, "chunks": 0, "deterministic": 0, "typesafe": 0, "unklar": 0, "ts_errors": 0}
    ts_budget = c.get("typesafe", {}).get("max_calls_per_run", 40)
    hi, lo_c = c.get("typesafe", {}).get("confidence_high", 0.75), c.get("typesafe", {}).get("confidence_low", 0.65)
    new_regs = []
    has_key = bool(typesafe_key())
    for path in sorted(glob.glob(P("inbox", "**", "*"), recursive=True)):
        if os.path.isdir(path) or os.path.basename(path).startswith((".", "_")) or "/_" in path.replace(P("inbox"), ""):
            continue
        sha = hashlib.sha1(open(path, "rb").read()).hexdigest()
        if sha in reg:
            continue
        text = extract_text(path)
        name = os.path.relpath(path, P("inbox"))
        src = {"id": "s_" + sha[:8], "file": name, "added": today.isoformat(), "chunks": 0}
        stats["files"] += 1
        for i, ch in enumerate(chunks(text)):
            if len(ch) < 200:
                continue
            stats["chunks"] += 1
            sc = score_chunk(ch, idx)
            if not sc:
                continue
            top, second = sc[0], (sc[1] if len(sc) > 1 else (0, None, 0))
            if top[2] < 2:                       # no substantive study content (e.g. organisational talk)
                stats["skipped"] = stats.get("skipped", 0) + 1
                continue
            choice, conf, how = top[1], None, "det"
            if not (top[0] >= 1.5 and top[0] >= 1.5 * second[0] and top[2] >= 3):
                if ts_budget > 0 and has_key:
                    cand = candidate_keys(sc)
                    crit = {f"{k[0]}:{k[1]}": lo_text.get(k, k[1]) for k in cand}
                    res = typesafe_choice(ch, crit, "Which learning objective does this study-material excerpt teach most directly? One answer.", c)
                    ts_budget -= 1
                    stats["typesafe"] += 1
                    if "error" in res:
                        stats["ts_errors"] += 1
                        how = "det-fallback"
                    elif res["confidence"] >= lo_c:
                        ex, lid = res["choice"].split(":", 1)
                        choice, conf, how = (ex, lid), res["confidence"], "typesafe" + ("" if res["confidence"] >= hi else "-low")
                    else:
                        stats["unklar"] += 1
                        continue
                else:
                    if top[2] < 3:
                        stats["unklar"] += 1
                        continue
                    how = "det-fallback"
                    stats["fallback"] = stats.get("fallback", 0) + 1
            else:
                stats["deterministic"] += 1
            key = f"{choice[0]}:{choice[1]}"
            excerpt = re.sub(r"\s+", " ", ch)[:320]
            index["by_lo"].setdefault(key, []).append({"src": src["id"], "file": name, "chunk": i, "how": how,
                                                     "conf": conf, "excerpt": excerpt, "date": today.isoformat()})
            src["chunks"] += 1
        index["sources"].append(src)
        new_regs.append({"sha1": sha, "file": name, "date": today.isoformat(), "chunks": src["chunks"]})
    if new_regs:
        new = not os.path.exists(reg_path)
        with open(reg_path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["sha1", "file", "date", "chunks"])
            if new:
                w.writeheader()
            w.writerows(new_regs)
        for k in index["by_lo"]:
            index["by_lo"][k] = index["by_lo"][k][-12:]   # keep the index small (token economy)
        jsave(P("data", "sources_index.json"), index)
    mapped = stats["deterministic"] + stats["typesafe"] + stats.get("fallback", 0)
    stats["deterministic_ratio"] = round(stats["deterministic"] / mapped, 2) if mapped else None
    return stats


# ----------------------------------------------------------------------------- briefing / recap / notebook
WD_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def de_date(d):
    return f"{WD_DE[d.weekday()]}, {d.strftime('%d.%m.%Y')}"


def fmt_pct(x):
    return f"{x:.0f} %"


def reading_lines(focus, weak_ids, los_by_id, budget=75, note=""):
    """Briefing section 'Lesen heute': Rita + PMBOK 8 (EN) pages per focus task, with a time guide (readplan.py)."""
    import readplan
    ids = list(focus) or weak_ids[:3]
    if 0 < len(ids) <= 4:                               # light days also catch up the biggest gaps
        ids += [w for w in weak_ids if w not in ids][:2]
    must, opt, total = readplan.plan(ids, los_by_id, budget)
    if not must:
        return []
    out = ["", f"## Lesen heute — Richtwert ca. {round(total / 5) * 5} Min (PMBOK 8 EN zuerst, Rita als Ergänzung; DE-Ausgabe bei Verständnisproblemen){note}"]
    out += [f"- {readplan.fmt_item(i)}" for i in must]
    if opt:
        out.append("- Danach optional: " + " · ".join(readplan.fmt_item(i) for i in opt))
    out.append("- *Richtwert, kein Pflichtpensum: Was der Kurs schon sicher abgedeckt hat, überfliegen. PMBOK 8 2,5 Min/Seite, Rita 1,5 Min/Seite (max. 25 Min je Kapitel).*")
    return out


def briefing(today, comp=None):
    c = cfg()
    comp = comp or compute(today)
    ph = comp.get("phase") or {}
    banks = load_banks()
    exam_key = ph.get("exam") if ph.get("exam") in banks else next((k for k in c.get("exams", {}) if k in banks), "itil5")
    ex = c["exams"][exam_key]
    k = comp.get(exam_key, {})
    rd = k.get("readiness", {})
    dp = c.get("day_plan", {}).get(today.isoformat(), {})
    days_left = (parse_day(ex["target_date"]) - today).days
    y = comp.get("yesterday", {})
    is_pmp = exam_key == "pmp"
    of = rd.get("of", 40)
    need, goal = round(of * ex.get("pass_pct", 65) / 100), round(of * ex.get("target_pct", 85) / 100)
    rita = {t["id"]: t.get("refs", {}).get("rita", []) for t in load_content()[1].get("los", [])} if is_pmp else {}
    lines = [f"# XLRTE Lerntag-Briefing — {de_date(today)}", "",
             f"Phase: **{ph.get('name', '—')}** ({ph.get('mode', '')}). Zielprüfung **{ex['name']}** am {parse_day(ex['target_date']).strftime('%d.%m.')} "
             f"({days_left} Tage){' — Termin noch NICHT gebucht' if not ex.get('booked') else ''}.", "",
             "## Wo stehen wir? (CI-Modell, Schritt 2)",
             f"- Prognose: **{rd.get('predicted', 0)} / {rd.get('of', 40)}** Punkte ({fmt_pct(rd.get('pct', 0))}), Bestehensschwelle ≈ {need}{' (PMI nennt keine feste Schwelle – Richtwert)' if is_pmp else ''}, Ziel {goal}. "
             f"Bestehenswahrscheinlichkeit (Schätzung): {fmt_pct(100 * rd.get('p_pass', 0))}. Evidenzabdeckung: {fmt_pct(rd.get('coverage', 0))}.",
             f"- Gestern: {y.get('retrievals', 0)} Abrufe, {y.get('correct', 0)}/{y.get('attempts', 0)} Fragen richtig, {y.get('focus_minutes', 0)} Fokusminuten.",
             f"- Fällige Wiederholungen heute: **{comp.get('srs_due', 0)}**. Streak: {comp.get('streak', 0)} Lerntage.", ""]
    if is_pmp:
        sh = studyhall_summary(read_events(), load_content()[1], today, c)
        yd = studyhall_day(read_events(), today - dt.timedelta(days=1 if today.weekday() != 0 else 3))
        if sh["entries"]:
            lines.insert(-1, "- Study Hall: " + (f"gestern {', '.join(yd)}; " if yd else "gestern nichts erfasst; ") + f"{sh['entries']} Einträge" + (f", letzte Full-Length {sh['last_full']}" if sh["last_full"] else "") + ".")
    ev = k.get("evm", {})
    if ev:
        lines += [f"- Lernprojekt (EVM): PV {ev['pv']} h · EV {ev['ev']} h · AC {ev['ac']} h · SPI {ev['spi'] or '—'} · CPI {ev['cpi'] or '—'}", ""]
    lines += ["## Wo wollen wir hin? — Plan für heute"]
    if dp:
        lines.append(f"**{dp.get('title', '')}**")
        lines += [f"- [ ] {t}" for t in dp.get("tasks", [])]
        gates = sorted((m for m in c.get("milestones", []) if m.get("exam") == exam_key and (m.get("type") == "gate" or m.get("critical")) and m.get("type") != "trap"
                        and m.get("due") and m["due"] >= today.isoformat()), key=lambda m: m["due"])[:6]
        if gates:
            lines += ["", "**Entscheidungstore bis zur Prüfung** (Status im Cockpit unter Prüfungen → Meilensteine):"]
            lines += [f"- ◆ {m['due'][8:10]}.{m['due'][5:7]}. (in {(dt.date.fromisoformat(m['due']) - today).days} Tagen): {m['title']}" for m in gates]
    if is_pmp:
        live_week = str(ph.get("name", "")).startswith("PMP Connected")      # Kurswoche: Wissensaufnahme, Pauken beginnt am Samstag danach
        lines += reading_lines(dp.get("focus_los", []), [w["id"] for w in k.get("weak", [])], {t["id"]: t for t in load_content()[1].get("los", [])},
                               budget=30 if live_week else 75, note=" · Kurswoche: nur leicht lesen, das Pauken beginnt am Samstag 10.10." if live_week else "")
    if is_pmp:
        stamp = "c_" + today.strftime("%Y%m%d")
        fresh = [c for c in (jload(P("data", "items_candidates.json"), []) or []) if str(c.get("id", "")).startswith(stamp) and c.get("exam") == "pmp"]
        if fresh:
            lines += ["", f"## Neue Fragen heute: {len(fresh)} (Training → „Neue Fragen“, dort gesammelt übernehmen)",
                      "- Aufgaben: " + ", ".join(sorted({c["lo"] for c in fresh})) + " · Ziel: deine Schwächen und Enabler ohne Frage"]
    if exam_key == "itil5":
        events = read_events()
        exam_events = [e for e in events if e["kind"] == "exam" and e.get("exam", exam_key) == exam_key]
        s1_ev = next((e for e in exam_events if e["ref"] == "XLRTE-S1"), None)
        s2_ev = next((e for e in exam_events if e["ref"] == "XLRTE-S2"), None)
        sp1_ev = next((e for e in reversed(exam_events) if e["ref"] == "SP1"), None)
        sp2_ev = next((e for e in reversed(exam_events) if e["ref"] == "SP2"), None)
        s1_str = f"{s1_ev.get('value', 0)}/40 Punkte ✓" if s1_ev else "ausstehend (Ziel ≥ 70 %)"
        s2_str = f"{s2_ev.get('value', 0)}/40 Punkte ✓" if s2_ev else "ausstehend (Ziel ≥ 75 %)"
        sp1_str = f"{sp1_ev.get('value', 0)}/40 Punkte ✓" if sp1_ev else "geschützt (Eichung vor Buchung, Ziel ≥ 75 %)"
        sp2_str = f"{sp2_ev.get('value', 0)}/40 Punkte ✓" if sp2_ev else "geschützt (Generalprobe vor Examen)"
        lines += ["", "## Prüfungskaskade & Burn-Schutz (Roadmap vor Buchung)",
                  f"- Stufe 1: Schattenprüfung S1 — {s1_str}",
                  f"- Stufe 2: Schattenprüfung S2 — {s2_str}",
                  f"- Stufe 3: Offizielle Musterprüfung SP1 — {sp1_str}",
                  f"- Stufe 4: Offizielle Musterprüfung SP2 — {sp2_str}",
                  "- *Hinweis: Offizielle PeopleCert-Musterprüfungen bleiben strikt vor dem täglichen Training isoliert.*"]
    lines += ["", "## Wertorientierung: die 5 teuersten Lücken (Prüfungsgewicht × Lücke)"]
    for w in k.get("weak", []):
        lines.append(f"- {w['id']} {w['text']} — Mastery {fmt_pct(100 * w['m'])}, ≈ {w['gap_points']} Punkte offen · "
                     + (", ".join(f"Rita Kap. {r['ch']} (S. {r['pages']})" for r in rita.get(w["id"], [])) if is_pmp else f"Buch §{w['book']}"))
    focus = ", ".join(dp.get("focus_los", [])) or ", ".join(w["id"] for w in k.get("weak", [])[:3])
    if is_pmp:
        lines += ["", "## Gemini Notebook — Prompts zum Kopieren", "", "**Audio-Briefing (Deep Dive, Englisch, ~10 Min):**",
                  f"> Create a deep-dive audio overview based only on my sources for the PMP exam (ECO 2026). Focus today: {focus}. "
                  "Use PMI mindset reasoning (\"what should the project manager do FIRST\"), contrast predictive vs. agile answers, end with three typical traps.",
                  "", "**Morgen-Quiz im Notebook:**",
                  f"> Ask me 10 PMP scenario questions (ECO 2026) on {focus}, one at a time, four options, reveal the answer with PMI rationale only after I respond.", ""]
    else:
        lines += ["", "## Gemini Notebook — Prompts zum Kopieren", "",
              "**Audio-Briefing (Deep Dive, Deutsch, ~10 Min):**",
              f"> Erstelle eine Audio-Zusammenfassung ausschließlich auf Basis meiner Quellen für die ITIL-5-Foundation-Prüfung. "
              f"Schwerpunkt heute: Syllabus-Abschnitte {focus}. Erkläre jede offizielle Definition wörtlich, stelle typische Verwechslungen "
              f"gegenüber und beende mit drei Prüfungsfallen. Zielgruppe: erfahrene IT-Führungskraft, keine Grundlagen zu IT.",
              "", "**Morgen-Quiz im Notebook:**",
              f"> Stelle mir 10 Multiple-Choice-Fragen im PeopleCert-Stil (BL1/BL2, vier Optionen, eine richtig) zu {focus}. "
              "Zeige die Lösung erst nach meiner Antwort und nenne die Quelle.", ""]
    txt = "\n".join(lines)
    os.makedirs(P("notebooklm"), exist_ok=True)
    with open(P("notebooklm", f"{today.isoformat()}_Briefing.md"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    return {"markdown": txt, "focus": focus, "plan": dp}


RANKS = [(0.85, "Value System Architect"), (0.65, "Service Architect in Training"), (0.5, "Practice Owner in Training"), (0.0, "Service Apprentice")]


def trap_section(items, events, today):
    """Profilabschnitt 'Fallen (PMP)'; leer, wenn data/traps_pmp.json fehlt."""
    traps = jload(P("data", "traps_pmp.json"), {})
    if not traps.get("taxonomy"):
        return []
    vis = trapstats.visible_items([i for i in items if i.get("exam") == "pmp"], events)
    return trapstats.profile_lines(trapstats.trap_stats(events, vis, traps, today), traps["taxonomy"])


KALIBER_MIN_WORDS = 40   # trainer: real stems ~55 words; PMI Mastery Builder 44


def caliber_section(items, events):
    """Profilabschnitt 'Prüfungskaliber (PMP)': Quote auf Fragen ab 40 Wörtern gegen kürzere. Fälle und Trainer-Sets bleiben draußen."""
    pool = [i for i in items if i.get("exam") == "pmp" and not i.get("case") and not i.get("drill")]
    big = {i["id"] for i in pool if len((i.get("q") or "").split()) >= KALIBER_MIN_WORDS}
    short = {i["id"] for i in pool} - big
    def rate(ids):
        a = [e for e in events if e.get("kind") == "attempt" and e.get("exam") == "pmp" and e.get("ref") in ids]
        return len(a), (sum(1 for e in a if (e.get("value") or 0) >= 1) / len(a) if a else None)
    nb, rb = rate(big); ns, rs = rate(short)
    lines = ["### Prüfungskaliber (PMP)", "",
             f"- Fragen im Pool mit Fragetext ab {KALIBER_MIN_WORDS} Wörtern: {len(big)} von {len(pool)}. Der Trainer beschreibt echte Fragen mit Ø ca. 55 Wörtern; Rohwerte auf kürzeren Fragen überschätzen die Prüfung."]
    if not nb:
        lines.append("- Prüfungskaliber: noch keine Abrufe. Nächster Schritt: Kaliber-Drill im Cockpit (Training) und Kaliber-Quiz im Notebook.")
    else:
        lines.append(f"- Prüfungskaliber: {nb} Abrufe, {round(100 * rb)} % · kürzere Fragen: {ns} Abrufe, {round(100 * rs) if ns else 0} %")
        if ns >= 5 and nb >= 5:
            gap = round(100 * (rs - rb))
            lines.append(f"- Abstand kurz gegen Kaliber: {gap} Pp" + (" → Kaliber-Drill priorisieren (Lesetempo, Fallen im langen Stamm)." if gap >= 10 else " → kein großer Abstand, weiter mischen."))
        else:
            lines.append("- Abstand noch nicht belastbar (unter 5 Abrufe je Gruppe).")
    return lines + [""]


def lab_section(today):
    """Abschnitt 'Lab-Fokus' (PMP): Schwachstellentraining ausserhalb der Reife-Messung, Auswahl in lab.py. Ein Fehler ist sichtbar, bricht das Profil aber nicht ab."""
    try:
        import lab
        return lab.focus_section(today).split("\n") + [""]
    except Exception as e:
        return ["### Lab-Fokus (Schwachstellentraining)", "", f"- nicht verfügbar: {type(e).__name__}: {e}", ""]


def learner_profile(today, comp=None):
    """Evidence-based ledger for the AI learning engine (Gemini Notebook). Every number comes from events/model — nothing estimated."""
    c = cfg()
    comp = comp or compute(today)
    syl, eco, items, gloss = load_content()
    events = read_events()
    ph = comp.get("phase") or {}
    banks = load_banks()
    ex_key = ph.get("exam") if ph.get("exam") in banks else next((k for k in c.get("exams", {}) if k in banks), "itil5")
    ex = c["exams"][ex_key]
    k = comp.get(ex_key, {})
    rd = k.get("readiness", {})
    is_pmp = ex_key == "pmp"
    bank = banks.get(ex_key) or (eco if is_pmp else syl)
    lo_by = {lo["id"]: lo for lo in bank.get("los", [])}
    it_by = {it["id"]: it for it in items if it.get("exam") == ex_key}
    att = [e for e in events if e["kind"] == "attempt" and e.get("exam") == ex_key and e["ref"] in it_by]
    # calibration (14 days)
    since = (today - dt.timedelta(days=13)).isoformat()
    sure = [e for e in att if e["date"] >= since and (e.get("meta") or {}).get("conf") == "sure"]
    sure_ok = sum(1 for e in sure if (e["value"] or 0) >= 1)
    cal = f"{round(100 * sure_ok / len(sure))} % ({sure_ok}/{len(sure)} „sicher“-Antworten richtig, 14 Tage)" if sure else "noch keine Daten"
    # velocity: retrievals of the last 3 study days vs. the 3 before
    days = sorted({e["date"] for e in events if e["kind"] in ("attempt", "card") and e["date"] <= today.isoformat()}, reverse=True)
    ret = [day_stats(events, parse_day(d))["retrievals"] for d in days[:6]]
    a, b = sum(ret[:3]), sum(ret[3:6])
    vel = "Stabil – noch zu wenig Verlauf" if not b else ("Hoch" if a > 1.15 * b else "Niedrig" if a < 0.85 * b else "Stabil")
    # hypercorrection queue: last "sure" answer wrong and not answered correctly since
    last = {}
    for e in sorted(att, key=lambda e: e.get("ts", "")):
        x = last.setdefault(e["ref"], {})
        if (e["value"] or 0) >= 1: x["ok"] = e.get("ts", "")
        elif (e.get("meta") or {}).get("conf") == "sure": x["sw"] = e.get("ts", "")
    hyper = [r for r, x in last.items() if x.get("sw") and not (x.get("ok", "") > x["sw"])]
    hyper_los = sorted({it_by[r]["lo"] for r in hyper})
    # Bloom / approach accuracy per category (all time)
    dim = (lambda it: it.get("appr", "?")) if is_pmp else (lambda it: f"BL{it.get('bl', 1)}")
    acc = {}
    for e in att:
        it = it_by[e["ref"]]; cat = lo_by.get(it["lo"], {}).get("cat", "?")
        v = acc.setdefault((cat, dim(it)), [0, 0]); v[1] += 1; v[0] += 1 if (e["value"] or 0) >= 1 else 0
    bloom = []
    for cat in bank.get("categories", []):
        cells = [f"{d} {round(100 * v[0] / v[1])} % (n={v[1]})" for (cc, d), v in sorted(acc.items()) if cc == cat["id"]]
        if not is_pmp:
            b1, b2 = acc.get((cat["id"], "BL1")), acc.get((cat["id"], "BL2"))
            step = ("mehr Evidenz sammeln (weniger als 5 BL1-Abrufe)" if not b1 or b1[1] < 5 else
                    "Begriffe festigen (BL1)" if b1[0] / b1[1] < .6 else
                    "Anwendung/Szenarien (BL2)" if b1[0] / b1[1] >= .8 else "gemischt BL1/BL2")
        else:
            step = "Szenarien (prädiktiv/agil/hybrid gemischt)"
        bloom.append(f"- {cat['id']} {cat['name']}: {' · '.join(cells) or 'noch keine Abrufe'} → nächste Stufe: {step}")
    # covered in plan/training before today
    topics = {t for d, p in c.get("day_plan", {}).items() if ex.get("plan_start", "0") <= d < today.isoformat() for t in p.get("focus_los", [])}
    covered = sorted(lo for lo in lo_by if any(lo == t or lo.startswith(t + ".") for t in topics))   # plan uses topic ids (1.1) or LO ids
    rank = next(r for t, r in RANKS if rd.get("pct", 0) / 100 >= t)
    weak = k.get("weak", [])
    dp = c.get("day_plan", {}).get(today.isoformat(), {})
    nxt = ", ".join(dp.get("focus_los", [])) or (weak[0]["id"] + " " + weak[0]["text"] if weak else "—")
    ref = (lambda lo: ", ".join(f"Rita Kap. {r['ch']}" for r in lo_by.get(lo, {}).get("refs", {}).get("rita", []))) if is_pmp \
        else (lambda lo: ("Buch §" + lo_by.get(lo, {}).get("book", "")) if lo_by.get(lo, {}).get("book") else "")
    cascade_lines = []
    if ex_key == "itil5":
        exam_events = [e for e in events if e["kind"] == "exam" and e.get("exam", ex_key) == ex_key]
        s1_ev = next((e for e in exam_events if e["ref"] == "XLRTE-S1"), None)
        s2_ev = next((e for e in exam_events if e["ref"] == "XLRTE-S2"), None)
        sp1_ev = next((e for e in reversed(exam_events) if e["ref"] == "SP1"), None)
        sp2_ev = next((e for e in reversed(exam_events) if e["ref"] == "SP2"), None)

        def fmt_ex(ev, name, target_pct):
            if not ev:
                return f"{name}: noch offen / ungesehen (Ziel: ≥ {target_pct} %)"
            val = ev.get("value", 0)
            of = (ev.get("meta") or {}).get("of", 40)
            pct_v = round(100 * float(val) / float(of)) if of else 0
            return f"{name}: {val}/{of} ({pct_v} %) ✓"

        if not s1_ev:
            next_step = "Stufe 1: Schattenprüfung S1 starten (40 ungesehene Fragen, 60 Min, blinder Trockenlauf)"
        elif not s2_ev:
            next_step = "Stufe 2: Schattenprüfung S2 starten (40 neue ungesehene Fragen, Stabilitätsnachweis vor Buchung)"
        elif not sp1_ev:
            next_step = "Stufe 3: Offizielle PeopleCert SP1 freischalten (Eichung; bei ≥ 75 % direkt Prüfung buchen!)"
        elif not sp2_ev:
            next_step = "Stufe 4: Offizielle PeopleCert SP2 als finale Generalprobe 24–48h vor dem Examen"
        else:
            next_step = "Alle Stufen erfolgreich absolviert – bereit für die offizielle Zertifizierung!"

        cascade_lines = [
            "- Boss Fight Status (4-Stufen-Kaskade vor Buchung):",
            f"  - 1. {fmt_ex(s1_ev, 'Schattenprüfung S1', 70)}",
            f"  - 2. {fmt_ex(s2_ev, 'Schattenprüfung S2', 75)}",
            f"  - 3. {fmt_ex(sp1_ev, 'Offizielle Musterprüfung SP1 (PeopleCert)', 75)}",
            f"  - 4. {fmt_ex(sp2_ev, 'Offizielle Musterprüfung SP2 (PeopleCert)', 80)}",
            f"  - Nächste Empfehlung: **{next_step}**",
            "- Burn-Schutz aktiv: SP1 & SP2 sind im System hinterlegt, aber aus regulärem Drill ausgeschlossen.",
        ]
    shs = studyhall_summary(events, eco, today, c) if is_pmp else {}
    lines = [f"## XLRTE Lernprofil — {de_date(today)} (für die Lern-Engine)", "",
             "Automatisch aus dem Lern-Log berechnet. Die Lern-Engine übernimmt diese Werte wörtlich und schätzt nichts selbst.", "",
             f"- Aktive Prüfung: **{ex['name']}** am {parse_day(ex['target_date']).strftime('%d.%m.%Y')} ({(parse_day(ex['target_date']) - today).days} Tage) · "
             f"Sprache der Prüfungsfragen: {'englisch' if is_pmp else 'deutsch'}",
             f"- Level / Role: {rank}",
             f"- SVH (Service Value Health): {round(rd.get('pct', 0))} % — Prognose {rd.get('predicted', 0)}/{rd.get('of', 0)} Punkte, "
             f"Bestehenswahrscheinlichkeit {round(100 * rd.get('p_pass', 0))} %, Evidenzabdeckung {round(rd.get('coverage', 0))} %",
             f"- Kalibrierung: {cal}",
             f"- Cognitive Velocity: {vel}" + (f" (Abrufe letzte 3 Lerntage {a} vs. davor {b})" if b else f" ({a} Abrufe bisher)"),
             "- Cognitive Debt (größte gewichtete Lücken): " + ("; ".join(f"{w['id']} {w['text']} ({round(100 * w['m'])} %, {ref(w['id'])})" for w in weak) or "keine"),
             *(["- Study-Hall-Belege je Task (Anzahl): " + (", ".join(f"{k} {v}" for k, v in sorted(shs["by_task"].items())) or "keine") + (f" · letzte Full-Length: {shs['last_full']}" if shs["last_full"] else "")] if is_pmp else []),
             "- Sicher & falsch (Hyperkorrektur zuerst): " + (", ".join(f"{lo} {lo_by[lo]['text']}" for lo in hyper_los if lo in lo_by) or "keine"),
             f"- Next Incident / Trigger: {nxt}",
             "- Bereits behandelt (Plan/offizielles Training bis gestern): "
             + (f"Themen {', '.join(sorted({lo.rsplit('.', 1)[0] if lo.count('.') > 1 else lo for lo in covered}))} ({len(covered)} Lernziele)" if covered else "noch nichts"),
             *cascade_lines, "",
             "### Bloom-/Ansatz-Profil je Kategorie", *bloom, ""]
    if is_pmp:
        lines += trap_section(items, events, today)
        lines += caliber_section(items, events)
        lines += lab_section(today)
    return "\n".join(lines)


def engine_prompt():
    """Split notebooklm/XLRTE_Lern_Engine_Prompt.md into the full and the short version (for the cockpit copy buttons)."""
    try:
        en = P("notebooklm", "XLRTE_Lern_Engine_Prompt.en.md")
        name = en if (cfg().get("language") == "en" and os.path.exists(en)) else P("notebooklm", "XLRTE_Lern_Engine_Prompt.md")
        t = open(name, encoding="utf-8").read()
    except OSError:
        return {"full": "", "short": ""}
    full = t.split("## Vollfassung", 1)[-1].split("## Kurzfassung", 1)[0].strip().strip("-").strip()
    short = t.split("## Kurzfassung", 1)[-1].split("\n", 1)[-1].strip() if "## Kurzfassung" in t else ""
    return {"full": full, "short": short}


def recap_day(day, events, items, syl, eco=None):
    st = day_stats(events, day)
    exams = [e for e in events if e["date"] == day.isoformat() and e["kind"] == "exam"]
    if not (st["retrievals"] or st["activities"] or exams):
        return None
    item_by = {it["id"]: it for it in items}
    lo_by = {lo["id"]: lo for lo in syl.get("los", [])}
    eco = eco if eco is not None else load_content()[1]
    for t in eco.get("los", []):
        lo_by[t["id"]] = dict(t, ref=", ".join(f"Rita Kap. {r['ch']}" for r in t.get("refs", {}).get("rita", [])))
    wrong = [e for e in events if e["date"] == day.isoformat() and e["kind"] == "attempt" and (e["value"] or 0) < 1]
    wl = {}
    for e in wrong:
        it = item_by.get(e["ref"])
        if it and it.get("lo"):
            wl[it["lo"]] = wl.get(it["lo"], 0) + 1
    wks = [e for e in events if e["date"] == day.isoformat() and e["kind"] == "workaround"]
    lines = [f"## {de_date(day)}", "",
             f"Abrufe: {st['retrievals']} · Fragen richtig: {st['correct']}/{st['attempts']} · Fokus: {st['focus_minutes']} Min", ""]
    if st["activities"]:
        lines.append("**Gelernt:** " + "; ".join((a.get("meta") or {}).get("text") or a["ref"] for a in st["activities"]))
    if exams:
        sim_names = {
            "XLRTE-SIM": "Prüfungssimulation", "XLRTE-SIM-MINI": "Mini-Simulation",
            "XLRTE-S1": "Schattenprüfung S1 (ungesehen)", "XLRTE-S2": "Schattenprüfung S2 (ungesehen)", "XLRTE-S3": "Schattenprüfung S3 (ungesehen)", "XLRTE-S4": "Schattenprüfung S4 (SP-Form, ungesehen)",
            "XLRTE-M1A": "PMP Mock 1 Teil A (ungesehen)", "XLRTE-M1B": "PMP Mock 1 Teil B (ungesehen)", "XLRTE-M1C": "PMP Mock 1 Teil C (ungesehen)", "XLRTE-M1": "PMP Vollmock 1 (180, ungesehen)", "XLRTE-M2A": "PMP Fallen-Mock 2 (ungesehen)", "XLRTE-M3A": "PMP Mock 3 im Prüfungskaliber (ungesehen)", "XLRTE-SZ1": "PMP Szenario-Set 1 (ungesehen)", "XLRTE-SZ2": "PMP Szenario-Set 2 (ungesehen)", "XLRTE-M2B": "PMP Mock 2 Teil B (ungesehen)", "XLRTE-M2C": "PMP Mock 2 Teil C (ungesehen)", "XLRTE-M2": "PMP Vollmock 2 (180, ungesehen)", "XLRTE-MBP": "PMI Übungsfragen People (ungesehen)", "XLRTE-MBR": "PMI Übungsfragen Process (ungesehen)", "XLRTE-MBB": "PMI Übungsfragen Business Environment (ungesehen)",
            "SP1": "Offizielle PeopleCert Musterprüfung SP1", "SP2": "Offizielle PeopleCert Musterprüfung SP2",
            "ITIL5-EXAM": "ITIL 5 Foundation Offizielle Prüfung"
        }
        lines.append("**Prüfungen / Simulationen:** " + "; ".join(f"{sim_names.get(e['ref'], e['ref'])}: {e.get('value', 0)}/{(e.get('meta') or {}).get('of', 40)} Punkte ({round(100 * float(e.get('value', 0)) / float((e.get('meta') or {}).get('of', 40)))} %)" for e in exams))
    if wl:
        lines += ["", "**Fehlerbilder (Incidents) nach Lernziel:**"]
        for lo, n in sorted(wl.items(), key=lambda x: -x[1]):
            t = lo_by.get(lo, {})
            lines.append(f"- {lo} {t.get('text', '')} — {n}× falsch ({t['ref'] if t.get('ref') else 'Buch §' + t.get('book', '')})")
    if wks:
        lines += ["", "**Known Errors mit Workaround (Merkhilfe):**"]
        lines += [f"- {w['ref']}: {(w.get('meta') or {}).get('text', '')}" for w in wks]
    return "\n".join(lines) + "\n"


def write_lab_basis():
    """Basis-Prompts des Labs als Notebook-Quelle. Ein Fehler hier stoppt den Tageslauf nie (Rueckgabe False)."""
    try:
        import lab
        txt = ("# XLRTE Lab — Basis-Prompts (A Tutor, B Multi-Level, C Propositionen)\nQuelle für Gemini Notebook; {THEMA} wird aus dem Abschnitt „Lab-Fokus“ des Lernprofils eingesetzt. Wird täglich neu erzeugt.\n\n"
               + lab.basis_prompts())
        with open(P("notebooklm", "XLRTE_Lab_Basis_Prompts.md"), "w", encoding="utf-8") as f:
            f.write(txt)
        return True
    except Exception:
        return False


def update_lernjournal(today):
    """Cumulative source document for Gemini Notebook: rebuilt from events (deterministic, idempotent)."""
    syl, eco, items, gloss = load_content()
    events = read_events()
    days = sorted({parse_day(e["date"]) for e in events if e["date"]}, reverse=True)
    prof = learner_profile(today)
    with open(P("notebooklm", "XLRTE_Lernprofil.md"), "w", encoding="utf-8") as f:
        f.write(prof + "\n")
    write_lab_basis()
    parts = ["# XLRTE Lernjournal",
             "Quelle für Gemini Notebook (NotebookLM). Wird täglich automatisch neu erzeugt; oben das aktuelle Lernprofil (PMP: inkl. Abschnitt „Lab-Fokus“), darunter neueste Tage zuerst.", "",
             prof]
    for d in days:
        r = recap_day(d, events, items, syl, eco)
        if r:
            parts.append(r)
    txt = "\n".join(parts)
    with open(P("notebooklm", "XLRTE_Lernjournal.md"), "w", encoding="utf-8") as f:
        f.write(txt)
    return len(days)


# ----------------------------------------------------------------------------- notes-vault bridge
def bridge(comp):
    syl, eco, items, gloss = load_content()
    events = read_events()
    wk = {}
    for e in events:
        if e["kind"] == "workaround":
            wk[e["ref"]] = (e.get("meta") or {}).get("text", "")
    solid = cfg().get("mastery", {}).get("solid", 0.8)
    mm = comp.get("itil5", {}).get("mastery", {})
    n = 0
    for lo in syl.get("los", []):
        m = mm.get(lo["id"], 0)
        if m < solid and lo["id"] not in wk:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", _norm(lo["text"]))[:50].strip("-")
        path = P("bridge", "to-notes-vault", "itil5", f"{lo['id']}-{slug}.md")
        terms = [g["term"] for g in gloss if lo["id"] in g.get("los", [])]
        body = ["---", f"title: \"ITIL 5 {lo['id']} {lo['text']}\"", "type: concept", "source: xlrte",
                f"status: {'solid' if m >= solid else 'known-error'}", f"mastery: {m:.2f}", f"book_ref: \"{lo.get('book', '')}\"",
                "tags: [itil5, certification, xlrte]", "---", "", f"# {lo['text']}", "",
                f"Syllabus {lo['id']} · Bloom-Stufe {lo['bl']} · Kategorie: {lo['topic_name']}", ""]
        if terms:
            body.append("Begriffe: " + ", ".join(f"[[{t}]]" for t in terms))
        if lo["id"] in wk:
            body += ["", "## Merkhilfe (eigener Workaround)", wk[lo["id"]]]
        txt = "\n".join(body) + "\n"
        if os.path.exists(path) and open(path, encoding="utf-8").read() == txt:
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        n += 1
    return n


# ----------------------------------------------------------------------------- render
def render(today, comp=None, brief=None):
    c = cfg()
    syl, eco, items, gloss = load_content()
    comp = comp or compute(today)
    brief = brief or briefing(today, comp)                  # nie ohne Briefing rendern: ein einzelnes `render` darf das Briefing im Cockpit nicht leeren
    data = {"generated": now_local().isoformat(timespec="minutes"), "today": today.isoformat(), "config": c,
            "syllabus": syl, "eco": eco, "items": items, "glossary": gloss, "course_notes": jload(P("data", "course_notes.json"), []) or [], "events": read_events(include_pretest=True), "cases": load_cases(),
            "engine": engine_prompt(), "profile": learner_profile(today, comp),
            "traps": jload(P("data", "traps_pmp.json"), {}),
            "banks": {k: b for k, (b, _, _) in load_packs().items()},
            "sources": jload(P("data", "sources_index.json"), {"sources": [], "by_lo": {}}),
            "briefing": brief or {}, "snapshot": comp, "runs": _last_runs()}
    import base64
    rd = lambda n: open(P("templates", n), encoding="utf-8").read()
    tpl = rd("cockpit.html")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    fav = "data:image/svg+xml;base64," + base64.b64encode(rd("x-monogram.svg").encode()).decode()
    html = (tpl.replace("<!--XLRTE_LOGO-->", rd("xlrte-logo.svg")).replace("<!--PE_MARK-->", rd("pe-mark.svg").replace('role="img"', 'role="img" class="pe"'))
            .replace("<!--FAVICON-->", fav).replace("<!--APP_JS-->", rd("app.js"))
            .replace("/*__XLRTE_DATA__*/", "window.XLRTE_DATA = " + payload + ";"))
    if "<!--I18N-->" in html:                                   # UI language: config "language" (de | en); the viewer can toggle
        try:
            i18n = ("<script>window.XLRTE_LANG = " + json.dumps(c.get("language") or "de") + "; window.XLRTE_I18N = " + rd("i18n_en.json").replace("</", "<\\/")
                    + ";</script><script>" + rd("i18n.js") + "</script>")
        except OSError:
            i18n = ""
        html = html.replace("<!--I18N-->", i18n)
    out = os.path.join(OUTDIR, "XLRTE_Cockpit.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out, len(html)


def _last_runs(n=7):
    path = P("state", "runs.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))[-n:]


# ----------------------------------------------------------------------------- check
def check_item(it, eco, case_ids):
    """Validation shared by check() and add_candidates() -> list of error strings (empty = ok)."""
    errs = []
    en_ids = {e["id"] for t in eco.get("los", []) for e in t.get("enablers", [])}
    opts, ans = it.get("options", []), it.get("answer")
    if it.get("type") == "num":      # Rechenübung: Zahleneingabe, 1–4 Felder mit Ergebnis und Toleranz, keine Optionen
        fl = it.get("fields") or []
        if not it.get("drill") or not 1 <= len(fl) <= 4 or opts:
            errs.append("num: nur als Drill, 1–4 Felder, keine Optionen")
        if not all(isinstance(f.get("label"), str) and isinstance(f.get("answer"), (int, float)) and not isinstance(f.get("answer"), bool)
                   and isinstance(f.get("tol", 0), (int, float)) and f.get("tol", 0) >= 0 for f in fl):
            errs.append("num: Feld braucht label, answer (Zahl), tol ≥ 0")
    elif it.get("drill"):      # Trainer-Drill: Optionszahl wie in der Quelle (4–6), Mehrfachauswahl mit beliebig vielen Schlüsseln
        n, keys = len(opts), (ans if isinstance(ans, list) else [ans])
        if not 4 <= n <= 6:
            errs.append("Drill: 4–6 Optionen")
        if not keys or not all(isinstance(a, int) and not isinstance(a, bool) and 0 <= a < n for a in keys) or len(set(keys)) != len(keys) or (it.get("type") == "multi") != (len(keys) > 1):
            errs.append("Drill: answer passt nicht zu type/Optionen")
    elif it.get("type") == "multi":
        if len(opts) != 5:
            errs.append("multi braucht 5 Optionen")
        if not (isinstance(ans, list) and len(ans) >= 2 and len(set(ans)) == len(ans)
                and all(isinstance(a, int) and not isinstance(a, bool) and 0 <= a < 5 for a in ans)):
            errs.append("multi: answer = Liste mit ≥ 2 Indizes 0–4")
    else:
        if len(opts) != 4:
            errs.append("braucht 4 Optionen")
        if not isinstance(ans, int) or isinstance(ans, bool) or not 0 <= ans < 4:
            errs.append("answer 0–3")
    if any(re.search(r"</?w:[a-z]|xml:space=", str(x)) for x in [it.get("q", ""), it.get("why", "")] + list(opts)):
        errs.append("Roh-XML aus Word-Import im Text")
    if len(set(str(o).strip().lower() for o in opts)) != len(opts):
        errs.append("doppelte Optionen")
    if len(it.get("why", "")) < (20 if it.get("exam") == "pmp" else 1):
        errs.append("Begründung fehlt/zu kurz")
    if it.get("case") and it["case"] not in case_ids:
        errs.append("unbekannter case " + str(it["case"]))
    if it.get("en") and (not str(it["en"]).startswith(str(it.get("lo", "")) + ".") or it["en"] not in en_ids):
        errs.append("en passt nicht zum Lernziel")
    return errs


def check():
    errs = []
    syl, eco, items, gloss = load_content()
    cases = load_cases()
    case_ids = {c["id"] for c in cases}
    los = {lo["id"] for b in load_banks().values() for lo in b.get("los", [])}
    seen = set()
    for it in items:
        if it["id"] in seen:
            errs.append(f"C1 doppelte Item-ID {it['id']}")
        seen.add(it["id"])
        if it.get("lo") not in los:
            errs.append(f"C2 {it['id']}: unbekanntes Lernziel {it.get('lo')}")
        for m in check_item(it, eco, case_ids):
            errs.append(f"C3 {it['id']}: {m}")
    for cs in cases:
        n = sum(1 for it in items if it.get("case") == cs["id"])
        if n < 3:
            errs.append(f"C6 Fall {cs['id']}: nur {n} Fragen (mind. 3)")
    ids = set()
    for e in read_events():
        if e["id"] in ids:
            errs.append(f"C5 doppelte Event-ID {e['id']}")
        ids.add(e["id"])
    return errs


# ----------------------------------------------------------------------------- candidate generation (LLM step, budgeted)
def gen_queue(today, limit=None):
    """Minimal context for the LLM step: LOs with fresh source excerpts and few approved items."""
    c = cfg()
    limit = limit or c.get("generation", {}).get("max_candidates_per_run", 8)
    syl, eco, items, gloss = load_content()
    comp = compute(today)
    if ((comp.get("phase") or {}).get("exam") or "") == "pmp" or os.environ.get("XLRTE_GEN_EXAM") == "pmp":
        import gen_pmp                                                  # PMP aktiv: Schwächen- und ECO-Enabler-getriebene Ziele (RUNBOOK Schritt 3)
        return gen_pmp.targets((comp.get("pmp") or {}).get("weak", []), items, eco, jload(P("data", "course_notes.json"), []) or [],
                               limit=max(limit, c.get("generation", {}).get("pmp_targets_per_run", 10)), today=today)
    idx = jload(P("data", "sources_index.json"), {"by_lo": {}}).get("by_lo", {})
    have = {}
    for it in items:
        have[(it["exam"], it["lo"])] = have.get((it["exam"], it["lo"]), 0) + 1
    los = {("itil5", lo["id"]): lo for lo in syl.get("los", [])}
    los.update({("pmp", t["id"]): t for t in eco.get("los", [])})
    q = []
    since = (today - dt.timedelta(days=3)).isoformat()
    for key, ex in idx.items():
        exam, lid = key.split(":", 1)
        fresh = [e for e in ex if e.get("date", "") >= since]
        if not fresh or (exam, lid) not in los:
            continue
        q.append({"exam": exam, "lo": lid, "lo_text": los[(exam, lid)]["text"], "bl": los[(exam, lid)].get("bl", 2),
                  "book": los[(exam, lid)].get("book", ""), "have_items": have.get((exam, lid), 0),
                  "excerpts": [e["excerpt"] for e in fresh[-3:]]})
    q.sort(key=lambda x: (x["have_items"], -len(x["excerpts"])))
    return q[:limit]


def add_candidates(path, today):
    new = jload(path, [])
    syl, eco, items, gloss = load_content()
    valid = {lo["id"] for b in load_banks().values() for lo in b.get("los", [])}
    case_ids = {cs["id"] for cs in load_cases()}
    pmp_los = {t["id"] for t in eco.get("los", [])}
    cur = jload(P("data", "items_candidates.json"), []) or []
    n0, ok, rej = len(cur), 0, []
    import gen_pmp
    shingles = gen_pmp.shingle_set(ROOT) if any((x.get("exam") or "pmp") == "pmp" and x.get("lo") in pmp_los for x in new) else set()
    stems_by_lo = {}
    for x in items + cur:
        if x.get("exam") == "pmp":
            stems_by_lo.setdefault(x["lo"], []).append(x["q"])
    accepted, tell = [], set()
    pre = [dict(x, exam=x.get("exam") or ("pmp" if x.get("lo") in pmp_los else "itil5")) for x in new]
    tell = gen_pmp.length_tell_rejects([x for x in pre if x["exam"] == "pmp"])
    pmp_pos = [k for k, x in enumerate(pre) if x["exam"] == "pmp"]
    tell = {pmp_pos[k] for k in tell}
    for i, it in enumerate(new):
        errs = [] if it.get("lo") in valid else ["lo"]
        exam = it.get("exam") or ("pmp" if it.get("lo") in pmp_los else "itil5")    # derive from the bank that owns the LO
        it = dict(it, exam=exam)
        if exam == "pmp":
            errs += [k for k in ("en", "appr") if not it.get(k)]                    # RUNBOOK: mandatory for PMP
            if it.get("appr") and it["appr"] not in ("predictive", "agile", "hybrid"): errs.append("appr")
        errs += check_item(it, eco, case_ids)
        if len(it.get("why", "")) < 20 and "why" not in errs: errs.append("why")
        if exam == "pmp" and not errs:                                              # gehärtete Zusatzprüfungen
            errs += gen_pmp.extra_errors(it, stems_by_lo.get(it["lo"], []), [a["q"] for a in accepted if a.get("lo") == it["lo"]], shingles)
            if i in tell:
                errs.append("Längen-Hinweis im Stapel (Lösung zu oft längste/kürzeste Option): Optionen angleichen")
        if errs:
            rej.append({"i": i, "errors": errs})
            continue
        cur.append({"id": f"c_{today.strftime('%Y%m%d')}_{n0 + ok + 1:02d}", "exam": exam, "lo": it["lo"],
                    "bl": it.get("bl", 2), "type": it.get("type", "std"), "q": it["q"], "options": it["options"],
                    "answer": it["answer"], "why": it["why"], "src": "gen:" + today.isoformat() + ":" + it.get("source", "inbox"),
                    "status": "candidate", **({"stmts": it["stmts"]} if it.get("stmts") else {}),
                    **{k: it[k] for k in ("en", "appr", "case") if it.get(k)}})
        accepted.append(it)
        ok += 1
    jsave(P("data", "items_candidates.json"), cur)
    return {"added": ok, "rejected": rej}


# ----------------------------------------------------------------------------- run
def run(today):
    for d in ("state", "inbox", "journal", "notebooklm", "bridge"):
        os.makedirs(P(d), exist_ok=True)
    report = {"date": today.isoformat()}
    errs = check()
    report["check_errors"] = len(errs)
    for e in errs[:10]:
        print("CHECK", e)
    report["journal"] = merge_journal()
    report["inbox"] = ingest_inbox(today)
    try:                                                                            # fresh deterministic drills, never fatal
        import gen_drills
        report["gen_drills"] = gen_drills.write(today)
    except Exception as e:
        report["gen_drills"] = {"error": str(e)[:80]}
    comp = compute(today)
    brief = briefing(today, comp)
    report["lernjournal_days"] = update_lernjournal(today)
    report["bridge_notes"] = bridge(comp)
    out, size = render(today, comp, brief)
    rd = comp.get("itil5", {}).get("readiness", {})
    report["readiness_itil5"] = f"{rd.get('predicted')}/{rd.get('of')} p_pass={rd.get('p_pass')}"
    rp = comp.get("pmp", {}).get("readiness", {})
    report["readiness_pmp"] = f"{rp.get('predicted')}/{rp.get('of')} p_pass={rp.get('p_pass')}"
    sh = studyhall_summary(read_events(), load_content()[1], today, cfg())
    report["studyhall"] = f"{sh['entries']} Einträge" + (f", letzte Full-Length {sh['last_full']}" if sh["last_full"] else "")
    report["html_kb"] = round(size / 1024)
    try:
        import eco_gate
        g = eco_gate.evaluate(eco_gate.load_items(ROOT), load_content()[1])
        report["eco_gate"] = {"items": g["n_items"], "enablers_covered": f"{g['stats']['enablers_covered']}/{g['stats']['enablers']}",
                              "domain_pct": g["stats"]["domain_pct"], "findings": g["findings"]}
    except Exception as e:                                                          # Prüfung darf den Tageslauf nie stoppen
        report["eco_gate"] = {"error": str(e)[:80]}
    path = P("state", "runs.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "ts", "events_added", "inbox_files", "chunks", "deterministic", "typesafe",
                                          "unklar", "readiness_itil5", "check_errors"])
        if new:
            w.writeheader()
        w.writerow({"date": today.isoformat(), "ts": now_local().isoformat(timespec="seconds"),
                    "events_added": report["journal"]["events_added"], "inbox_files": report["inbox"]["files"],
                    "chunks": report["inbox"]["chunks"], "deterministic": report["inbox"]["deterministic"],
                    "typesafe": report["inbox"]["typesafe"], "unklar": report["inbox"]["unklar"],
                    "readiness_itil5": report["readiness_itil5"], "check_errors": report["check_errors"]})
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "merge-journal", "ingest-inbox", "ingest-glossary", "status", "briefing", "render",
                                    "check", "bridge", "lernjournal", "gen-queue", "add-candidates", "eco-gate"])
    ap.add_argument("--file")
    ap.add_argument("--today")
    ap.add_argument("--pdf")
    a = ap.parse_args()
    today = parse_day(a.today) if a.today else today_local()
    if a.cmd == "run":
        run(today)
    elif a.cmd == "merge-journal":
        print(merge_journal())
    elif a.cmd == "ingest-inbox":
        print(ingest_inbox(today))
    elif a.cmd == "ingest-glossary":
        print(ingest_glossary(a.pdf), "Begriffe")
    elif a.cmd == "status":
        print(json.dumps(compute(today), ensure_ascii=False, indent=1)[:4000])
    elif a.cmd == "briefing":
        print(briefing(today)["markdown"])
    elif a.cmd == "render":
        print(render(today))
    elif a.cmd == "lernjournal":
        print(update_lernjournal(today))
    elif a.cmd == "bridge":
        print(bridge(compute(today)))
    elif a.cmd == "eco-gate":
        import eco_gate
        g = eco_gate.evaluate(eco_gate.load_items(ROOT), load_content()[1])
        print(json.dumps(g["stats"] | {"findings": g["findings"], "enablers_zero": g["stats"]["enablers_zero"][:40]}, ensure_ascii=False, indent=1))
    elif a.cmd == "gen-queue":
        print(json.dumps(gen_queue(today), ensure_ascii=False, indent=1))
    elif a.cmd == "add-candidates":
        print(json.dumps(add_candidates(a.file, today), ensure_ascii=False))
    elif a.cmd == "check":
        errs = check()
        print("\n".join(errs) or "OK")
        sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
