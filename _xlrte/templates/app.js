"use strict";
/* XLRTE Cockpit — client. Event-sourced: every action is an event; all figures are recomputed from events. */
const D = window.XLRTE_DATA || {};
const C = D.config || {};
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt1 = x => (Math.round(x * 10) / 10).toLocaleString("de-DE");
const pct = x => Math.round(x * 100) + " %";
const localISO = (d = new Date()) => d.toLocaleDateString("sv-SE");
let TODAY = localISO();   /* re-checked on focus: a tab left open overnight must not stamp events with yesterday */
const dayDiff = (a, b) => Math.round((new Date(b + "T12:00") - new Date(a + "T12:00")) / 864e5);
const WD = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"];
const deDate = iso => { const d = new Date(iso + "T12:00"); return WD[d.getDay()] + ", " + d.toLocaleDateString("de-DE"); };
const LS = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode: in-memory only */ } }
};
function toast(m) { const t = $("#toast"); t.textContent = m; t.classList.add("on"); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("on"), 2200); }
function copy(text) { (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(() => toast("In die Zwischenablage kopiert"), () => { prompt("Kopieren:", text); }); }

/* ---------------------------------------------------------------- events */
const embeddedIds = new Set((D.events || []).map(e => e.id));
let pending = LS.get("xlrte.pending.v2", []).filter(e => !embeddedIds.has(e.id));
LS.set("xlrte.pending.v2", pending);
let EVENTS = [], VORAB = [];
/* Vorab-Test (Pretesting): Versuche mit meta.mode "vorab" liegen ausserhalb von EVENTS – Fehler sind gewollt und zählen nicht für Prognose, Wiederholung, Fehler-Management */
function splitVorab(all) { const vorab = [], rest = []; all.forEach(e => ((e.kind === "attempt" && (e.meta || {}).mode === "vorab") ? vorab : rest).push(e)); return { rest, vorab }; }
/* 3 Fragen zum Tagesthema: je Task eine, ungesehene zuerst (pure, rnd injizierbar) */
function vorabPick(pool, tasks, seen, rnd, n = 3) {
  const by = {}; tasks.forEach(t => by[t] = shuffleWith(pool.filter(i => i.lo === t), rnd).sort((a, b) => seen.has(a.id) - seen.has(b.id)));
  const order = shuffleWith(tasks.filter(t => by[t].length), rnd), out = [];
  for (let r = 0; out.length < n; r++) { let any = false; order.forEach(t => { if (out.length < n && by[t][r]) { out.push(by[t][r]); any = true; } }); if (!any) break; }
  return out;
}
function rebuildEvents() { const all = (D.events || []).concat(pending).sort((a, b) => (a.ts || "").localeCompare(b.ts || "")); const voided = new Set(all.filter(e => e.kind === "setting" && e.ref === "void").map(e => e.value)); const sp = splitVorab(all.filter(e => !voided.has(e.id))); EVENTS = sp.rest; VORAB = sp.vorab; }
rebuildEvents();
function uid() { return "e_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }
function addEvent(kind, f = {}) {
  const e = Object.assign({ id: uid(), ts: new Date().toISOString().slice(0, 19), date: localISO(), kind, exam: state.exam, ref: "", value: "", minutes: 0, meta: {} }, f);
  pending.push(e); LS.set("xlrte.pending.v2", pending); rebuildEvents(); invalidate();
  scheduleExport();
  return e;
}
/* Boolean-Settings kommen aus dem CSV-Log als True/False zurück (Großschreibung), im Browser als true/false */
function isTrue(v) { return v === true || v === 1 || /^(true|1)$/i.test(String(v)); }
function settings() { const s = {}; EVENTS.filter(e => e.kind === "setting").forEach(e => s[e.ref] = e.value); return s; }

/* ---------------------------------------------------------------- state */
const state = { exam: null, view: "cockpit", cache: {} };
function currentPhase() {
  const ph = (C.phases || []).find(p => p.from <= TODAY && TODAY <= p.to) || (C.phases || []).find(p => p.from > TODAY);
  return ph || { name: "–", exam: examList()[0] || "itil5", attendance_course: "", mode: "" };
}
/* Exams = every key in config.exams whose bank has learning objectives (legacy ITIL/PMP files or a pack in packs/). */
function examList() { return Object.keys(C.exams || {}).filter(k => { const b = bank(k); return b && (b.los || []).length; }); }
const COURSE = C.course ? !!C.course.attendance : true;   // course attendance (login/logout form); off = daily recap only
state.exam = (x => examList().includes(x) ? x : null)(LS.get("xlrte.exam", null)) || (examList().includes(currentPhase().exam) ? currentPhase().exam : (examList()[0] || "itil5"));
function invalidate() { state.cache = {}; renderAll(); }
function examCfg(x = state.exam) {
  const base = Object.assign({}, (C.exams || {})[x] || {}); const s = settings();
  if (s[x + ".target_date"]) base.target_date = s[x + ".target_date"];
  if (s[x + ".booked"] !== undefined) base.booked = isTrue(s[x + ".booked"]);
  return base;
}
function bank(x = state.exam) { const b = x === "pmp" ? D.eco : x === "itil5" ? D.syllabus : (D.banks || {})[x]; return b && b.los ? b : { los: [], categories: [] }; }
function rejected() { const r = new Set(); EVENTS.filter(e => e.kind === "review").forEach(e => { if (+e.value === 0) r.add(e.ref); else r.delete(e.ref); }); return r; }
function glossary(x = state.exam) { return (D.glossary || []).filter(g => (g.exam || "itil5") === x); }
/* Schattenprüfungen S1 & S2: ungesehene, SP-kalibrierte Fragen – bis zum ersten Durchlauf aus allen anderen Modi ausgeblendet; offizielle SP1/SP2 in Quarantäne */
function s1Event() { return EVENTS.filter(e => e.kind === "exam" && e.ref === "XLRTE-S1").slice(-1)[0]; }
function s2Event() { return EVENTS.filter(e => e.kind === "exam" && e.ref === "XLRTE-S2").slice(-1)[0]; }
function s3Event() { return EVENTS.filter(e => e.kind === "exam" && e.ref === "XLRTE-S3").slice(-1)[0]; }
function s4Event() { return EVENTS.filter(e => e.kind === "exam" && e.ref === "XLRTE-S4").slice(-1)[0]; }
/* PMP-Mock-Prüfungen (Mock 1 = Teile M1A/M1B/M1C à 60 Fragen, oder komplett 180): ungesehen bis zum ersten Durchlauf eines Teils oder des Vollmocks */
/* Kursnotizen: KI-Zusammenfassungen der Trainersitzungen, automatisch dem Task zugeordnet (scripts/course_notes.py). Ungeprüft; Zweifelsfälle mit Warnung. */
function courseNotesHTML(id) {
  const ns = (D.course_notes || []).filter(n => (n.los || []).includes(id));
  if (!ns.length) return "";
  return `<details class="small" style="margin-top:6px"><summary><b>Kursnotizen (${ns.length})</b> · KI-Zusammenfassung der Trainersitzungen, ungeprüft, Zuordnung automatisch</summary><ul>`
    + ns.slice(0, 40).map(n => `<li>${n.warn ? `<span title="${esc(n.warn)}">⚠ </span>` : ""}${esc(n.text)} <span class="tiny muted">(${esc(n.src.slice(0, 40))})</span>${n.warn ? `<div class="tiny" style="color:#E4572E">Achtung: ${esc(n.warn)}</div>` : ""}</li>`).join("")
    + `</ul></details>`;
}
/* Fall-Modus "Fragen zuerst" (Trainer-Taktik): bei Fallstudien zuerst die zugehörigen Fragen überfliegen (Suchauftrag), dann den Fall lesen. Immer im Modus "fall", sonst per Setting ui.qfirst (Standard aus). */
function qfirstOn(mode) { return mode === "fall" || isTrue(settings()["ui.qfirst"]); }
function casePreviewHTML(cs, qs) {
  return `<div class="casebox"><div class="label">Fall · ${esc(cs.title)} · Schritt 1 von 2: Fragen überfliegen</div>
    <div class="small muted" style="margin:6px 0">Lies jetzt nur die ${qs.length} Fragen (ca. 30 Sekunden), ohne Antworten. Sie geben deinem Kopf einen Suchauftrag für den Fall.</div>
    <ol class="stmts">${qs.map(q => `<li>${esc(q.q)}</li>`).join("")}</ol></div>`;
}
function pickCaseRun(cases, visible, seenIds, rnd = Math.random) {
  const by = {}; visible.filter(i => i.case).forEach(i => (by[i.case] = by[i.case] || []).push(i));
  const ok = (cases || []).filter(c => (by[c.id] || []).length >= 3);
  if (!ok.length) return [];
  const fresh = ok.filter(c => !by[c.id].some(i => seenIds.has(i.id)));
  const pool = fresh.length ? fresh : ok, c = pool[Math.floor(rnd() * pool.length)];
  return by[c.id].slice().sort((a, b) => a.id.localeCompare(b.id));
}
/* Shot Clock (Pacing): Zeit je Frage = Gesamtlimit / Fragenzahl (PMP 180/240 Min = 80 s). Erste Frage eines Falls +60 s (Fall lesen). Die Uhr stoppt nichts, sie zeigt Überzug in Rot. */
const SHOT_CASE_BONUS = 60;
function shotOn() { const v = settings()["ui.shotclock"]; return v === undefined || isTrue(v); }
function shotBudget(limitSec, n, firstOfCase) { return Math.max(20, Math.floor(limitSec / Math.max(1, n))) + (firstOfCase ? SHOT_CASE_BONUS : 0); }
function shotState(rem, budget) { return rem < 0 ? "over" : rem <= 10 ? "urgent" : rem <= budget * 0.25 ? "warn" : "ok"; }
function fmtShot(rem) { const a = Math.abs(rem); return (rem < 0 ? "+" : "") + Math.floor(a / 60) + ":" + String(a % 60).padStart(2, "0"); }
function paceSummary(answers) {
  const a = (answers || []).filter(x => x.secs !== undefined && x.budget); if (!a.length) return null;
  const avg = Math.round(a.reduce((s, x) => s + x.secs, 0) / a.length), bud = Math.round(a.reduce((s, x) => s + x.budget, 0) / a.length);
  const over = a.filter(x => x.secs > x.budget).length;
  const slow = a.map((x, k) => ({ n: (answers.indexOf(x) + 1), secs: x.secs, over: x.secs - x.budget })).sort((p, q) => q.over - p.over).filter(x => x.over > 0).slice(0, 3);
  return { n: a.length, avg, bud, over, slow, okSecs: Math.round(a.filter(x => x.ok).reduce((s, x) => s + x.secs, 0) / Math.max(1, a.filter(x => x.ok).length)), wrongSecs: Math.round(a.filter(x => !x.ok).reduce((s, x) => s + x.secs, 0) / Math.max(1, a.filter(x => !x.ok).length)) };
}
function stemWords(list) { const w = (list || []).map(i => String(i.q || "").split(/\s+/).filter(Boolean).length).filter(Boolean).sort((x, y) => x - y); return w.length ? { n: w.length, med: w[Math.floor(w.length / 2)], max: w[w.length - 1] } : null; }
function stemHTML(list) { const s = stemWords(list); if (!s) return ""; const tip = s.med >= 40 ? "Prüfungskaliber (Trainer: Ø ca. 55 Wörter)." : "Kürzer als die Prüfung (Trainer: Ø ca. 55 Wörter): das Lesetempo wird hier eher unterschätzt."; return `<div class="small muted" style="margin-top:8px">Fragelänge: Median ${s.med} Wörter, längste ${s.max}. ${tip}</div>`; }
function paceHTML(p) {
  if (!p) return "";
  const tip = p.avg > p.bud ? `Im Schnitt ${p.avg - p.bud} s über dem Budget: früher markieren und weitergehen, statt auf Sicherheit zu warten.` : `Im Tempo: im Schnitt ${p.bud - p.avg} s unter dem Budget. Die Zeitreserve kannst du für Fälle und Rechenfragen nutzen.`;
  return `<table style="margin-top:10px"><tr><th>Pacing (Shot Clock)</th><th class="num">Wert</th></tr><tr><td>Budget je Frage (Ø)</td><td class="num">${p.bud} s</td></tr><tr><td>Tatsächlich (Ø)</td><td class="num">${p.avg} s</td></tr><tr><td>Fragen über Budget</td><td class="num">${p.over} / ${p.n}</td></tr><tr><td>Richtige / falsche Antworten (Ø)</td><td class="num">${p.okSecs} s / ${p.wrongSecs} s</td></tr>${p.slow.length ? `<tr><td>Größter Überzug</td><td class="num">${p.slow.map(x => `Frage ${x.n} (+${x.over} s)`).join(", ")}</td></tr>` : ""}</table><div class="small muted" style="margin-top:4px">${tip}</div>${shotOn() ? "" : `<button class="btn ghost sm" id="shotBack" style="margin-top:6px">Shot Clock wieder einblenden</button>`}`;
}
function wireShot() { const c = $("#shotChip"); if (c) c.onclick = () => { addEvent("setting", { ref: "ui.shotclock", value: false }); c.remove(); }; if (run && run.limit) simTick(); }
/* Kartenrückseite: erst Kurzfassung und Eselsbrücke (falls vorhanden, scripts/glossary_hints.py), darunter der offizielle Wortlaut */
function hasHint(g) { return !!(g.hint_short || g.hint_eb || settings()["mn." + g.id]); }
function cardBackHTML(g) {
  const own = settings()["mn." + g.id];
  const extra = (g.hint_short ? `<div><b>Kurz:</b> ${esc(g.hint_short)}</div>` : "") + (g.hint_eb ? `<div style="margin-top:4px"><b>Eselsbrücke:</b> ${esc(g.hint_eb)}</div>` : "") + (own ? `<div style="margin-top:4px"><b>Meine:</b> ${esc(own)}</div>` : "");
  return extra ? `${extra}<div class="muted" style="margin-top:8px"><span class="tiny">Offizieller Wortlaut</span><br>${esc(g.definition)}</div>` : esc(g.definition);
}
/* Neue Fragen: Kandidaten ohne Bewertung (review-Ereignis); Sammelfreigabe */
function openCands(its, events) { const rv = new Set(events.filter(e => e.kind === "review").map(e => e.ref)); return its.filter(i => i.status === "candidate" && !rv.has(i.id)); }
/* gemeistert: letzte zwei Versuche richtig, nicht geraten, an verschiedenen Tagen -> aus Schwächen- und Lernziel-Drills heraushalten (Wiederholung bleibt) */
function masteredIds(events) {
  const by = {}; events.filter(e => e.kind === "attempt" && e.exam === "pmp").forEach(e => (by[e.ref] = by[e.ref] || []).push(e));
  const out = new Set();
  Object.keys(by).forEach(id => { const a = by[id].slice(-2); if (a.length === 2 && a.every(x => +x.value === 1 && (x.meta || {}).conf !== "guess") && a[0].date !== a[1].date) out.add(id); });
  return out;
}
function paceTrendHTML(events) {
  const ps = events.filter(e => e.kind === "note" && e.ref === "pace").slice(-6); if (!ps.length) return "";
  return `<div class="card" style="margin-top:10px"><div class="label">Pacing-Verlauf (Shot Clock)</div><table class="small"><tr><th>Datum</th><th>Modus</th><th class="num">Ø Sekunden</th><th class="num">Budget</th><th class="num">Über Budget</th></tr>`
    + ps.map(e => { const m = e.meta || {}; return `<tr><td>${esc(e.date)}</td><td>${esc(m.mode || "")}</td><td class="num">${+e.value}</td><td class="num">${m.bud}</td><td class="num">${m.over}/${m.n}</td></tr>`; }).join("") + `</table></div>`;
}
function candPanelHTML(list) {
  if (!list.length) return "";
  return `<div class="card" style="margin-bottom:10px"><div class="label">Neue Fragen · ${list.length} offen</div>
    <div class="small muted" style="margin:4px 0">Vom täglichen Lauf aus deinen Schwächen erzeugt. Haken = übernehmen, ohne Haken = verwerfen.</div>
    <div style="max-height:260px;overflow:auto"><table class="small">${list.map(i => `<tr><td><input type="checkbox" data-cand="${esc(i.id)}" checked></td><td>${esc(i.en || i.lo)}</td><td>${esc(i.appr || "")}</td><td>${esc(i.q.slice(0, 130))}${i.q.length > 130 ? "…" : ""}</td></tr>`).join("")}</table></div>
    <div class="row" style="margin-top:8px"><button class="btn sm" id="candOk">Ausgewählte übernehmen, Rest verwerfen</button><button class="btn ghost sm" id="candAll">Alle übernehmen</button><button class="btn ghost sm" id="candDrill">Jetzt üben</button></div></div>`;
}
function heatStyle(q, n) { if (!n) return "background:rgba(228,87,46,.25)"; if (q === null) return "background:rgba(128,128,128,.12)"; return q >= .8 ? "background:rgba(60,160,90,.25)" : q >= .6 ? "background:rgba(230,170,40,.30)" : "background:rgba(228,87,46,.30)"; }
/* "Wo wollen wir hin?": die nächsten Entscheidungstore (Meilensteine vom Typ gate oder kritisch) mit Restzeit und Kriterium, damit sie präsent sind */
function gatesHTML() {
  const set = settings(), ex = (C.phase_exam || ((C.phases || []).find(p => p.from <= TODAY && TODAY <= p.to) || {}).exam || "pmp");
  const light = realityLight(realityMeasures(EVENTS, "pmp", examCfg("pmp").reality_discount_pp || { own: 10, official: 5 }), examCfg("pmp").target_pct || 75).light;
  const ctx = { events: EVENTS, set, light };
  const days = d => Math.round((new Date(d + "T12:00:00Z") - new Date(TODAY + "T12:00:00Z")) / 864e5);
  const rows = (C.milestones || []).filter(m => m.exam === ex && (m.type === "gate" || m.critical) && m.type !== "trap")
    .map(m => { const due = msDue(m, examCfg(m.exam)); return Object.assign({}, m, { dueD: due, st: msStatus(m, due, TODAY, ctx) }); })
    .filter(m => m.st !== "done" && m.dueD).sort((a, b) => a.dueD.localeCompare(b.dueD)).slice(0, 6);
  if (!rows.length) return "";
  return `<div style="margin-top:8px;padding-top:6px;border-top:1px solid var(--line)"><div class="label">Entscheidungstore bis zur Prüfung</div>`
    + rows.map(m => { const n = days(m.dueD); const when = n < 0 ? `<b style="color:#c0392b">${-n} Tage überfällig</b>` : n === 0 ? "<b>heute</b>" : n === 1 ? "morgen" : `in ${n} Tagen`;
      return `<div class="small" style="margin:5px 0">◆ <b>${esc(m.title)}</b> <span class="muted">· ${esc(m.dueD.slice(8, 10) + "." + m.dueD.slice(5, 7) + ".")}, ${when}</span>${m.note ? `<div class="muted">${esc(m.note.length > 170 ? m.note.slice(0, 168) + "…" : m.note)}</div>` : ""}</div>`; }).join("") + `</div>`;
}
function mockEvent(ref) { return EVENTS.filter(e => e.kind === "exam" && e.ref === ref).slice(-1)[0]; }
/* abgebrochene Läufe (weniger als 80 % beantwortet) verbrauchen den ungesehenen Satz nicht */
function mockDone(ref) { const e = mockEvent(ref); if (!e) return undefined; const m = e.meta || {}, of = +m.of || 0; return of && m.answered !== undefined && +m.answered < 0.8 * of ? undefined : e; }
function mockSeen(i) { return !i.mock || !!mockDone("XLRTE-" + i.set) || !!mockDone("XLRTE-" + i.mock); }
const MOCK_MODES = { m1a: ["M1A"], m1b: ["M1B"], m1c: ["M1C"], m1: ["M1A", "M1B", "M1C"], m2a: ["M2A"], m3a: ["M3A"], sz1: ["SZ1"], sz2: ["SZ2"], m2b: ["M2B"], m2c: ["M2C"], m2: ["M2A", "M2B", "M2C"], mbp: ["MBP"], mbr: ["MBR"], mbb: ["MBB"] };
/* Kursbezug je ECO-Task: PMI-Kurs (Kursanbieter), Lessons und Workbook-Seiten laut Inhaltsverzeichnis des Student Workbook v4.1; "~" = aus dem Lektionstitel abgeleitet */
const COURSE_LESSONS = { 1: ["Introduction", "1–10"], 2: ["Setting the Foundation", "11–30"], 3: ["Stakeholders, Vision, and Communication", "31–76"], 4: ["Team, Conflict, and Knowledge", "77–112"], 5: ["Scope, Value, Resources, Finance, and Risk", "113–188"], 6: ["Method, Plan, Schedule, Quality, and Procurement", "189–246"], 7: ["Execution, Monitoring, Change, and Impediments", "247–278"], 8: ["Business Environment Dynamics, Continuous Improvement, and Closure", "279–296"], 9: ["Next Steps", "297–"] };
const COURSE_TASKS = { "P.1": [3], "P.4": [3], "P.5": [3], "P.6": [3], "P.8": [3], "P.2": [4], "P.3": [4], "P.7": [4], "PR.2": [5], "PR.3": [5], "PR.4": [5], "PR.6": [5], "BE.5": [5], "PR.1": [6], "PR.8": [6], "PR.7": [6], "PR.5": [6], "PR.9": [7], "BE.3": [7], "BE.4": [7], "BE.1": [2, 7], "BE.2": [2, 7], "BE.6": [8], "BE.7": [8], "BE.8": [8], "PR.10": [8] };
const courseRef = id => (COURSE_TASKS[id] || []).map(n => `Lesson ${n} „${COURSE_LESSONS[n][0]}“ (Workbook S. ${COURSE_LESSONS[n][1]})`).join(" · ");
const isMock = mode => Object.prototype.hasOwnProperty.call(MOCK_MODES, mode);
function items(x = state.exam) { const rej = rejected(), hideS1 = !s1Event(), hideS2 = !s2Event(), hideS3 = !s3Event(), hideS4 = !s4Event(); return (D.items || []).filter(i => i.exam === x && !rej.has(i.id) && !(hideS1 && i.set === "S1") && !(hideS2 && i.set === "S2") && !(hideS3 && i.set === "S3") && !(hideS4 && i.set === "S4") && mockSeen(i) && !i.drill && i.status !== "official_sp"); }

/* ---------------------------------------------------------------- model (mirrors scripts/xlrte.py) */
/* PMI Study Hall (nur Zahlen, nie Inhalte): Beleg je Task (n × W_TASK) oder je Domäne gleichmäßig auf deren Tasks (n × W_DOMAIN); Gesamtwert allein ist kein Beleg; Mini × 0,8; ext_void entwertet. Spiegel: ext_evidence in scripts/xlrte.py */
function shVoided(evs) { return new Set(evs.filter(e => e.kind === "ext_void").map(e => e.ref)); }
function shValid(evs, x) { const v = shVoided(evs); return evs.filter(e => e.kind === "ext" && e.exam === x && !v.has(e.id) && (e.meta || {}).src === "studyhall"); }
function shEvidence(evs, x, B, M, asOf) {
  const W = Object.assign({ W_TASK: 1, W_DOMAIN: .3, mini: .8 }, (M || {}).ext || {}), out = [];
  const ids = new Set(B.los.map(l => l.id)), byCat = {}; B.los.forEach(l => (byCat[l.cat] = byCat[l.cat] || []).push(l.id));
  shValid(evs, x).forEach(e => {
    if (e.date > asOf) return;
    const m = e.meta || {}, f = m.type === "mini" ? W.mini : 1, age = Math.max(0, dayDiff(e.date, asOf));
    const bt = m.by_task || {}, tasks = Object.keys(bt).filter(t => ids.has(t) && bt[t][1] > 0);
    if (tasks.length) tasks.forEach(t => out.push({ lo: t, age, c: bt[t][0] / bt[t][1], w: bt[t][1] * W.W_TASK * f, e }));
    else Object.keys(m.by_domain || {}).forEach(d => { const v = m.by_domain[d], L = byCat[d] || []; if (!L.length || !(v[1] > 0)) return; L.forEach(t => out.push({ lo: t, age, c: v[0] / v[1], w: v[1] * W.W_DOMAIN * f / L.length, e })); });
  });
  return out;
}
function shValidate(f) {
  const n = +f.of, c = +f.value, errs = [], sum = (o, i) => Object.values(o || {}).reduce((a, v) => a + (+v[i] || 0), 0);
  if (!(n > 0) || !Number.isInteger(n)) errs.push("Gesamtzahl muss eine ganze Zahl > 0 sein");
  if (!(c >= 0 && c <= n) || !Number.isInteger(c)) errs.push("Richtig muss zwischen 0 und gesamt liegen");
  [f.by_domain, f.by_task].forEach(o => Object.keys(o || {}).forEach(k => { const v = o[k]; if (!(v[1] > 0) || !(v[0] >= 0 && v[0] <= v[1])) errs.push("Zeile " + k + ": 0 ≤ richtig ≤ gesamt, gesamt > 0"); }));
  if (sum(f.by_domain, 1) > n || sum(f.by_domain, 0) > c) errs.push("Summe der Domänen übersteigt den Gesamtwert");
  if (sum(f.by_task, 1) > n || sum(f.by_task, 0) > c) errs.push("Summe der Tasks übersteigt den Gesamtwert");
  return errs;
}
function shProtectDate(ref, ex) { const d = (ex.studyhall_protect_days || { "SH-FULL1": 14, "SH-FULL2": 5 })[ref]; if (!d || !ex.target_date) return null; const t = new Date(ex.target_date + "T12:00:00Z"); t.setUTCDate(t.getUTCDate() - d); return t.toISOString().slice(0, 10); }
function model(x = state.exam, asOf = TODAY) {
  if (asOf === TODAY && state.cache[x]) return state.cache[x];
  const B = bank(x) || { los: [], categories: [] };
  const M = C.mastery || { half_life_days: 10, prior_a: .5, prior_b: 1.5, solid: .8 };
  const itemLo = {}; (D.items || []).forEach(i => { if (i.exam === x) itemLo[i.id] = i.lo; });
  const cardLo = {}; glossary(x).forEach(g => cardLo[g.id] = g.los || []);
  const ev = {}; const push = (lo, age, c, w, e) => (ev[lo] = ev[lo] || []).push({ age, c, w, e });
  const evs = asOf === TODAY ? EVENTS : EVENTS.filter(e => e.date <= asOf);
  evs.forEach(e => {
    if (e.exam !== x) return;
    const age = Math.max(0, dayDiff(e.date, asOf));
    if (e.kind === "attempt" && itemLo[e.ref]) {
      let c = +e.value || 0; if (c >= 1 && (e.meta || {}).conf === "guess") c = .5; push(itemLo[e.ref], age, c, 1, e);
    } else if (e.kind === "card" && cardLo[e.ref]) cardLo[e.ref].forEach(lo => push(lo, age, (+e.value || 0) >= 2 ? 1 : 0, .5, e));
  });
  if (x === "pmp") shEvidence(evs, x, B, M, asOf).forEach(o => (ev[o.lo] = ev[o.lo] || []).push(o));
  const mm = {};
  B.los.forEach(lo => {
    let sw = 0, sc = 0; (ev[lo.id] || []).forEach(o => { const w = o.w * Math.pow(.5, o.age / M.half_life_days); sw += w; sc += w * o.c; });
    mm[lo.id] = { m: (M.prior_a + sc) / (M.prior_a + M.prior_b + sw), n: sw, att: (ev[lo.id] || []).filter(o => o.e && o.e.kind === "attempt").map(o => o.e) };
  });
  const byCat = {}; B.los.forEach(lo => (byCat[lo.cat] = byCat[lo.cat] || []).push(lo.id));
  const lw = {}; B.categories.forEach(c => (byCat[c.id] || []).forEach(id => lw[id] = c.weight / 100 / byCat[c.id].length));
  const Q = B.questions || (x === "pmp" ? 180 : 40);
  let pred = 0, cov = 0;
  const cats = B.categories.map(c => {
    const ids = byCat[c.id] || []; const m = ids.length ? ids.reduce((s, i) => s + mm[i].m, 0) / ids.length : .25;
    const q = Q * c.weight / 100; pred += q * m; return { id: c.id, name: c.name, weight: c.weight, m, q, exp: q * m };
  });
  B.los.forEach(lo => { if (mm[lo.id].n >= 1.5) cov += lw[lo.id] || 0; });
  const p = pred / Q, unc = 6 * (1 - cov) * (Q / 40) + 1.5 * (Q / 40);
  const sd = Math.sqrt(Q * p * (1 - p) + unc * unc);
  const ex = examCfg(x); const need = Q * (ex.pass_pct || 65) / 100 - .5;
  const pPass = .5 * (1 + erf((pred - need) / (sd * Math.SQRT2)));
  const weak = B.los.slice().sort((a, b) => lw[b.id] * (1 - mm[b.id].m) - lw[a.id] * (1 - mm[a.id].m)).slice(0, 5)
    .map(lo => ({ lo, m: mm[lo.id].m, gap: Q * lw[lo.id] * (1 - mm[lo.id].m) }));
  const out = { B, mm, lw, Q, pred, p, cov, sd, pPass, cats, weak };
  if (asOf === TODAY) state.cache[x] = out; return out;
}
function erf(x) { const t = 1 / (1 + .3275911 * Math.abs(x)); const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - .284496736) * t + .254829592) * t * Math.exp(-x * x); return x >= 0 ? y : -y; }

function srs() {
  if (state.cache.srs) return state.cache.srs;
  const iv = C.srs_intervals_days || [0, 1, 2, 4, 8, 16]; const st = {};
  EVENTS.forEach(e => {
    if (e.kind !== "attempt" && e.kind !== "card") return;
    const s = st[e.ref] || (st[e.ref] = { box: 0 }); const good = (+e.value || 0) >= (e.kind === "card" ? 2 : 1); const guess = (e.meta || {}).conf === "guess";
    if (good && !guess) s.box = Math.min(iv.length - 1, s.box + 1); else if (!good) s.box = 1;
    s.last = e.date; const d = new Date(e.date + "T12:00"); d.setDate(d.getDate() + iv[s.box]); s.due = localISO(d); s.kind = e.kind;
  });
  return (state.cache.srs = st);
}
function dueList(x = state.exam) {
  const st = srs(); const ids = new Set(items(x).map(i => i.id)); glossary(x).forEach(g => ids.add(g.id));
  return Object.keys(st).filter(k => ids.has(k) && st[k].due <= TODAY);
}
function dayStats(d = TODAY, x = null) {
  const es = EVENTS.filter(e => e.date === d && (!x || e.exam === x));
  const att = es.filter(e => e.kind === "attempt"), cards = es.filter(e => e.kind === "card");
  return { att: att.length, ok: att.filter(e => +e.value >= 1).length, cards: cards.length, ret: att.length + cards.length,
    focus: es.filter(e => e.kind === "focus" || e.kind === "activity").reduce((s, e) => s + (+e.minutes || 0), 0),
    acts: es.filter(e => e.kind === "activity"), att_events: att, es };
}
function streak() {
  const need = C.streak_min || { retrievals: 25, focus_minutes: 60 }; let s = 0; const d = new Date(TODAY + "T12:00");
  for (let i = 0; i < 120; i++) {
    const iso = localISO(d); const wd = d.getDay();
    if (wd !== 0 && wd !== 6) { const st = dayStats(iso); const ok = st.ret >= need.retrievals || (st.focus >= need.focus_minutes && st.ret >= 10); if (ok) s++; else if (iso !== TODAY) break; }
    d.setDate(d.getDate() - 1);
  }
  return s;
}
function xp() {
  let x = 0; const seen = new Set(); const perDayFocus = {};
  EVENTS.forEach(e => {
    if (e.kind === "attempt" && +e.value >= 1) { const k = e.ref + e.date; if (!seen.has(k)) { seen.add(k); x += (e.meta || {}).conf === "guess" ? 1 : 2; } }
    else if (e.kind === "card") x += 1;
    else if (e.kind === "focus" || e.kind === "activity") { const f = perDayFocus[e.date] || 0; const add = Math.min(48 - f, Math.floor((+e.minutes || 0) / 10)); if (add > 0) { perDayFocus[e.date] = f + add; x += add; } }
    else if (e.kind === "workaround") x += 15;
    else if (e.kind === "exam" && (e.meta || {}).pass) x += (e.ref === "XLRTE-SIM-MINI" || /^XLRTE-M\d[ABC]$/.test(e.ref)) ? 30 : 100;
  });
  examList().forEach(k => { const m = model(k); x += 10 * Object.values(m.mm).filter(v => v.m >= (C.mastery || {}).solid).length; });
  let lvl = 1, need = 250, rest = x; while (rest >= need) { rest -= need; lvl++; need = 250 * lvl; }
  return { x, lvl, rest, need };
}

/* ---------------------------------------------------------------- incidents / problems */
function incidentBoard(x = state.exam) {
  const itemsById = {}; (D.items || []).forEach(i => itemsById[i.id] = i);
  const since = (() => { const d = new Date(TODAY + "T12:00"); d.setDate(d.getDate() - 14); return localISO(d); })();
  const wrong = EVENTS.filter(e => e.exam === x && e.kind === "attempt" && +e.value < 1 && e.date >= since);
  const byLo = {}; wrong.forEach(e => { const it = itemsById[e.ref]; if (!it) return; (byLo[it.lo] = byLo[it.lo] || []).push(e); });
  const wk = {}; EVENTS.filter(e => e.kind === "workaround" && e.exam === x).forEach(e => wk[e.ref] = e);
  const m = model(x); const res = { inc: [], prob: [], ke: [], solved: [] };
  const last3ok = lo => { const a = (m.mm[lo] || { att: [] }).att.slice(-3); return a.length >= 3 && a.every(e => +e.value >= 1 && (e.meta || {}).conf !== "guess"); };
  Object.keys(byLo).forEach(lo => {
    const n = byLo[lo].length;
    if (wk[lo]) (last3ok(lo) && byLo[lo].slice(-1)[0].ts < (m.mm[lo].att.slice(-1)[0] || {}).ts ? res.solved : res.ke).push({ lo, n, wk: wk[lo] });
    else if (n >= 2) res.prob.push({ lo, n });
    else res.inc.push({ lo, n, e: byLo[lo][0] });
  });
  Object.keys(wk).forEach(lo => { if (!byLo[lo]) (last3ok(lo) ? res.solved : res.ke).push({ lo, n: 0, wk: wk[lo] }); });
  return res;
}

/* ---------------------------------------------------------------- header & nav */
function loById(id, x = state.exam) { return (bank(x).los || []).find(l => l.id === id) || { id, text: id, book: "" }; }
function renderHeader() {
  $$("#examSeg button").forEach(b => b.classList.toggle("on", b.dataset.x === state.exam));
  const ex = examCfg(); const d = dayDiff(TODAY, ex.target_date);
  $("#chipCountdown").innerHTML = `${esc(ex.name)} · <b>${d >= 0 ? d + " Tage" : "vorbei"}</b>${ex.booked ? "" : " · <span class='status-bad'>nicht gebucht</span>"}`;
  $("#chipStreak").innerHTML = `Streak <b>${streak()}</b>`;
  const X = xp(); $("#chipLevel").innerHTML = `Level <b>${X.lvl}</b> · ${X.x.toLocaleString("de-DE")} XP`;
  $("#chipLevel").title = `${X.rest}/${X.need} XP bis Level ${X.lvl + 1}. XP nur für Evidenz: richtige Abrufe, Karten, Fokuszeit (gedeckelt), Workarounds, gefestigte Lernziele.`;
}
function go(v) { state.view = v; $$("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.v === v)); $$(".view").forEach(s => s.classList.toggle("on", s.id === "v-" + v)); renderView(); window.scrollTo(0, 0); }
$("#tabs").addEventListener("click", e => { const b = e.target.closest("button"); if (b) go(b.dataset.v); });
$("#examSeg").innerHTML = examList().map(x => `<button data-x="${esc(x)}">${esc(examCfg(x).short || examCfg(x).name || x)}</button>`).join("");
if ($(".brand .sub")) $(".brand .sub").textContent = "Lernsystem · " + examList().map(x => examCfg(x).short || examCfg(x).name || x).join(" & ");
if (!COURSE) { const jt = document.querySelector('#tabs button[data-v="journal"]'); if (jt) jt.textContent = "Journal & Recap"; }
$("#examSeg").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; state.exam = b.dataset.x; LS.set("xlrte.exam", state.exam); invalidate(); });
(function theme() {
  const t = LS.get("xlrte.theme", null); if (t) document.documentElement.dataset.theme = t;
  $("#themeBtn").onclick = () => { const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"); const n = cur === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = n; LS.set("xlrte.theme", n); };
})();
document.addEventListener("click", e => { const g = e.target.closest("[data-go]"); if (!g) return; go("training"); startMode(g.dataset.go, g.dataset.lo); });

/* ---------------------------------------------------------------- cockpit */
function renderCockpit() {
  const m = model(), ex = examCfg(), ph = currentPhase();
  const target = m.Q * (ex.target_pct || 85) / 100, pass = m.Q * (ex.pass_pct || 65) / 100;
  $("#heroNum").innerHTML = `${fmt1(m.pred)} <small>/ ${m.Q} Punkte</small>`;
  $("#heroPass").textContent = pct(m.pPass);
  $("#heroMeter").innerHTML = `<div class="fill" style="width:${(m.pred / m.Q * 100).toFixed(1)}%"></div><div class="mark" style="left:${pass / m.Q * 100}%" title="Bestehen ${pass}"></div><div class="mark acc" style="left:${target / m.Q * 100}%" title="Ziel ${target}"></div>`;
  $("#heroLegend").innerHTML = `<span>0</span><span>Bestehen ${Math.ceil(pass)} · Ziel ${Math.round(target)} (${ex.target_pct} %)</span><span>${m.Q}</span>`;
  const st = dayStats(TODAY, state.exam);
  const since = localISO(new Date(Date.now() - 13 * 864e5)), cal = calibration(EVENTS, state.exam, since);
  $("#heroKpis").innerHTML = [["Evidenzabdeckung", pct(m.cov), ""], ["Heute abgerufen", st.ret, ""], ["Heute richtig", st.att ? pct(st.ok / st.att) : "–", ""], ["Fällig", dueList().length, ""],
    ["„Sicher“ stimmt", cal.rate === null ? "–" : pct(cal.rate), `Kalibrierung (14 Tage): ${cal.ok} von ${cal.n} als „sicher“ markierten Antworten waren richtig. Unter 90 %: Distraktoren genauer lesen. Offene „sicher & falsch“: ${hyperItems().length}.`]]
    .map(([l, v, t]) => `<div class="kpi" ${t ? `title="${esc(t)}"` : ""}><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  $("#heroWhy").textContent = m.cov < .5 ? "Schätzung mit großer Unsicherheit: Für Lernziele ohne Abrufe setzt das Modell Ratewahrscheinlichkeit (25 %) an. Jeder Abruf macht die Prognose ehrlicher." : "Prognose = Σ Kategorie-Gewicht × Beherrschung (Abrufe der letzten Tage, Halbwertszeit 10 Tage)." + (state.exam === "itil5" ? " Kalibriere sie über die 4-Stufen-Kaskade (S1 → S2 → SP1 → SP2 im Reiter Prüfungen)." : " Kalibriere sie mit Simulationen im Reiter Prüfungen.");
  // SLA
  const sla = Object.assign({ retrievals: 40, focus_minutes: 300, logout_by: "17:00", recap_by: "21:00" }, C.sla || {});
  const logout = COURSE ? EVENTS.find(e => e.date === TODAY && e.kind === "attendance" && e.ref === "logout") : EVENTS.find(e => e.date === TODAY && e.kind === "recap");
  const rows = [["Abrufe (Fragen + Karten)", st.ret, sla.retrievals, ""], ["Lern- und Fokuszeit", st.focus, sla.focus_minutes, " Min"]];
  let ok = 0;
  $("#slaRows").innerHTML = rows.map(([l, v, t, u]) => { const r = Math.min(1, v / t); if (r >= 1) ok++; return `<div class="bars"><div class="b ${r >= 1 ? "" : ""}"><span>${l}</span><div class="track"><span style="width:${r * 100}%;background:${r >= 1 ? "var(--ink)" : "var(--neutral)"}"></span></div><span class="n">${v}/${t}${u}</span></div></div>`; }).join("")
    + `<div class="bars"><div class="b"><span>${COURSE ? "Logout bis " + sla.logout_by : "Tages-Recap bis " + sla.recap_by}</span><div class="track"><span style="width:${logout ? 100 : 0}%;background:var(--ink)"></span></div><span class="n">${logout ? logout.ts.slice(11, 16) : "offen"}</span></div></div>`;
  if (logout) ok++;
  $("#slaState").textContent = ok === 3 ? "SLA erfüllt" : `${ok}/3 erfüllt`; $("#slaState").className = "pill " + (ok === 3 ? "solid" : "");
  // CI steps
  const dp = (C.day_plan || {})[TODAY] || {};
  $("#dayTitle").textContent = deDate(TODAY) + (dp.title ? " · " + dp.title : "") ;
  const login = EVENTS.find(e => e.date === TODAY && e.kind === "attendance" && e.ref === "login");
  const planDone = new Set(EVENTS.filter(e => e.date === TODAY && e.kind === "note" && e.ref === "plan").map(e => e.value));
  const tasks = (dp.tasks || []).map((t, i) => `<label class="row small" style="gap:6px;margin:3px 0"><input type="checkbox" data-plan="${i}" ${planDone.has(i) || planDone.has(String(i)) ? "checked" : ""}> ${esc(t)}</label>`).join("") || `<span class="small muted">Kein Tagesplan hinterlegt – Phase: ${esc(ph.name)}. Arbeite die teuersten Lücken ab.</span>`;
  const brief = D.briefing && D.today === TODAY;
  const steps = [
    ["Was ist unsere Vision?", `${esc(ex.name)} am ${new Date(ex.target_date + "T12:00").toLocaleDateString("de-DE")} mit ≥ ${ex.target_pct} % – nicht nur bestehen, sondern souverän.`, true],
    ["Wo stehen wir jetzt?", `${COURSE ? `Kurs-Login um ${(C.core_hours || {}).login || "09:00"} ` + (login ? "<b>erfasst " + login.ts.slice(11, 16) + "</b>" : "<button class='btn sm' id='ciLogin'>Login erfassen</button>") + " · " : "Tagesstart: "}${brief ? "<a href='#' data-view='notebook'>Briefing lesen</a>" : "Briefing: nächster Lauf"} · Prognose ${fmt1(m.pred)}/${m.Q}`, COURSE ? !!login : st.ret > 0],
    ["Wo wollen wir hin?", tasks + gatesHTML(), dp.tasks && planDone.size >= (dp.tasks || []).length],
    ["Wie kommen wir dorthin?", `Top-Lücke: <b>${esc(m.weak[0] ? m.weak[0].lo.id + " " + m.weak[0].lo.text : "–")}</b>`, false],
    ["Maßnahmen ergreifen", `Fokusblöcke (Dock unten rechts) + Training. Heute ${st.focus} Min, ${st.ret} Abrufe.`, st.ret >= (C.sla || {}).retrievals],
    ["Kommen wir voran?", `Lern-SLA ${ok}/3 · Incidents heute: ${st.att - st.ok}`, ok === 3],
    ["Wie stellen wir sicher, dass die Verbesserungen relevant bleiben?", COURSE ? `Logout-Text, Journal-Export, Recap im Gemini Notebook. <a href="#" data-view="journal">Zum Tagesabschluss</a>` : `Tages-Recap: dein Tag gegen deinen bisherigen Lernzeitraum, dann Journal-Export. <a href="#" data-view="journal">Zum Recap</a>`, !!logout]
  ];
  const nowIdx = steps.findIndex(s => !s[2]);
  $("#ciSteps").innerHTML = steps.map((s, i) => `<li class="${s[2] ? "done" : i === nowIdx ? "now" : ""}"><div class="q">${s[0]}</div><div class="small">${s[1]}</div></li>`).join("");
  const cl = $("#ciLogin"); if (cl) cl.onclick = () => { addEvent("attendance", { ref: "login", exam: currentExamForAttendance() }); toast("Login erfasst – jetzt im Teams-Formular bestätigen"); };
  $$("#ciSteps [data-plan]").forEach(cb => cb.onchange = () => addEvent("note", { ref: "plan", value: +cb.dataset.plan, meta: { done: cb.checked, text: (dp.tasks || [])[+cb.dataset.plan] } }));
  $$("#ciSteps [data-view]").forEach(a => a.onclick = ev => { ev.preventDefault(); go(a.dataset.view); });
  // weak
  $("#weakList").innerHTML = m.weak.map(w => `<div class="row small" style="padding:6px 0;border-bottom:1px solid var(--line);justify-content:space-between;flex-wrap:nowrap"><span style="min-width:0"><b>${w.lo.id}</b> ${esc(w.lo.text)} <span class="muted">· Buch §${esc(w.lo.book || "–")}</span></span><span class="muted" style="white-space:nowrap">≈ ${fmt1(w.gap)} P.</span></div>`).join("");
  $("#dueCount").textContent = "(" + dueList().length + ")";
  // cat bars
  const minCat = m.cats.reduce((a, b) => (b.q - b.exp > a.q - a.exp ? b : a), m.cats[0] || {});
  $("#catBars").innerHTML = m.cats.map(c => `<div class="b ${c === minCat ? "hi" : ""}" data-tip="${esc(c.name)}: Beherrschung ${pct(c.m)} · ${fmt1(c.exp)} von ${fmt1(c.q)} Punkten · Gewicht ${c.weight} %"><span>${esc(c.id)} · ${esc(c.name)}</span><div class="track"><span style="width:${c.m * 100}%"></span></div><span class="n">${fmt1(c.exp)}/${fmt1(c.q)}</span></div>`).join("");
  // badges
  const inc = incidentBoard("itil5"); const allEx = EVENTS.filter(e => e.kind === "exam");
  const solidN = Object.values(model("itil5").mm).filter(v => v.m >= (C.mastery || {}).solid).length;
  const badges = [
    ["Erster Abruf", EVENTS.some(e => e.kind === "attempt")], ["Streak 5", streak() >= 5], ["10 Lernziele gefestigt", solidN >= 10],
    ["Kategorie 4 ≥ 80 %", (model("itil5").cats.find(c => c.id === "4") || {}).m >= .8], ["Erster Known Error", inc.ke.length + inc.solved.length > 0],
    ["3 Known Errors gelöst", inc.solved.length >= 3], ["Schattenprüfung S1 ≥ 70 %", allEx.some(e => e.ref === "XLRTE-S1" && +e.value / (+(e.meta || {}).of || 40) >= .7)],
    ["Schattenprüfung S2 ≥ 75 %", allEx.some(e => e.ref === "XLRTE-S2" && +e.value / (+(e.meta || {}).of || 40) >= .75)],
    ["SP1 ≥ 80 %", allEx.some(e => e.ref === "SP1" && +e.value / (+(e.meta || {}).of || 40) >= .8)],
    ["SP2 ≥ 85 %", allEx.some(e => e.ref === "SP2" && +e.value / (+(e.meta || {}).of || 40) >= .85)], ["ITIL 5 Foundation bestanden", allEx.some(e => e.ref === "ITIL5-EXAM" && (e.meta || {}).pass)],
    ["500 Abrufe", EVENTS.filter(e => e.kind === "attempt" || e.kind === "card").length >= 500]];
  $("#badges").innerHTML = badges.map(([n, on]) => `<span class="badge ${on ? "on" : ""}">${on ? "✓ " : ""}${n}</span>`).join("");
  const runs = D.runs || []; const lr = runs[runs.length - 1];
  $("#sysInfo").innerHTML = `Stand der Daten: <b>${esc((D.generated || "").replace("T", " "))}</b>${D.today !== TODAY ? " <span class='status-warn'>(nicht von heute – täglicher Lauf ausstehend)</span>" : ""}<br>
    Fragenbank: ${items("itil5").length} aktiv (${(D.items || []).filter(i => (i.exam || "itil5") === "itil5").length} inkl. S1/S2/SP) ITIL · ${items("pmp").length} PMP · Karten: ${glossary("itil5").length} ITIL · ${glossary("pmp").length} PMP · Quellen im Index: ${((D.sources || {}).sources || []).length}<br>
    Nicht synchronisierte Einträge: <b>${pending.length}</b>${lr ? `<br>Letzter Lauf: ${esc(lr.date)} · +${esc(lr.events_added)} Events · Inbox ${esc(lr.inbox_files)} Datei(en), ${esc(lr.deterministic)} deterministisch / ${esc(lr.typesafe)} TypeSafe` : ""}`;
}

/* ---------------------------------------------------------------- lernpfad */
function renderPfad() {
  const m = model(), B = m.B, q = ($("#pfadSearch").value || "").toLowerCase(); const solid = (C.mastery || {}).solid || .8;
  const explore = state.exam === "pmp" && LS.get("xlrte.pfadMode", "pfad") === "explore";
  $("#pfadMode").innerHTML = state.exam === "pmp" ? `<div class="seg"><button data-pm="pfad" class="${explore ? "" : "on"}">Lernpfad</button><button data-pm="explore" class="${explore ? "on" : ""}">Erkundung</button></div>` : "";
  $$("#pfadMode [data-pm]").forEach(b => b.onclick = () => { LS.set("xlrte.pfadMode", b.dataset.pm); renderPfad(); });
  if (explore) return renderExplore(q);
  $("#pfadTitle").textContent = "Lernpfad · " + (state.exam === "pmp" ? "PMP ECO 2026" : state.exam === "itil5" ? "ITIL 5 Foundation Syllabus" : (bank().name || examCfg().name || state.exam));
  $("#pfadSub").textContent = state.exam === "pmp" ? "26 Tasks in 3 Domänen · People 33 % · Process 41 % · Business Environment 26 % (ECO gültig ab 09.07.2026)" : `${B.los.length} Lernziele · 40 Fragen · 40 % BL1 / 60 % BL2 · Buchverweise = Abschnitte im offiziellen Buch (VitalSource)`;
  const open = LS.get("xlrte.openCats", {});
  $("#pfadList").innerHTML = B.categories.map(c => {
    const los = B.los.filter(l => l.cat === c.id && (!q || (l.id + " " + l.text + " " + (l.focus || "")).toLowerCase().includes(q)));
    if (!los.length) return "";
    const cm = m.cats.find(x => x.id === c.id);
    return `<details class="cat" data-cat="${c.id}" ${open[c.id] || q ? "open" : ""}><summary><div><h3>${esc(c.id)} · ${esc(c.name)}</h3><div class="small muted">${c.weight} % · ≈ ${fmt1(cm.q)} Fragen · ${los.length} Lernziele</div></div><div class="mini"><span style="width:${cm.m * 100}%"></span></div><div class="small" style="text-align:right">${pct(cm.m)}</div></summary><div class="body">`
      + los.map(l => { const v = m.mm[l.id]; const src = ((D.sources || {}).by_lo || {})[state.exam + ":" + l.id] || [];
        return `<div class="lo-row" data-lo="${l.id}"><span class="id">${l.id}</span><span>${esc(l.text)}${l.focus ? `<div class="tiny muted">${esc(l.focus)}</div>` : ""}</span><span class="pill">${l.bl ? "BL" + l.bl : ""}</span><span class="tiny muted">${l.book ? "Buch §" + esc(l.book) : ritaRef(l)}${src.length ? " · " + src.length + " Quellen" : ""}</span><span><div class="mini"><span style="width:${v.m * 100}%;background:${v.m >= solid ? "var(--ink)" : "var(--neutral)"}"></span></div><div class="tiny muted" style="text-align:right">${pct(v.m)} · n=${fmt1(v.n)}</div></span></div>`; }).join("")
      + `</div></details>`;
  }).join("");
  $$("#pfadList details").forEach(d => d.addEventListener("toggle", () => { const o = LS.get("xlrte.openCats", {}); o[d.dataset.cat] = d.open; LS.set("xlrte.openCats", o); }));
  $$("#pfadList .lo-row").forEach(r => r.onclick = () => openLo(r.dataset.lo));
  const dpv = (C.day_plan || {})[TODAY] || {};
  if (state.exam === "pmp" && (dpv.focus_los || []).length && !q) { const t = VORAB.filter(e => e.date === TODAY);
    $("#pfadList").insertAdjacentHTML("afterbegin", `<div class="card" style="margin-bottom:12px"><div class="label">Heute · ${esc(dpv.title || "")}</div><div class="small muted" style="margin:6px 0">Vorab-Test: 3 Fragen zum Tagesthema (${esc(dpv.focus_los.slice(0, 4).join(", "))}${dpv.focus_los.length > 4 ? " …" : ""}), ohne Vorwissen. Fehler sind gewollt, zählt nicht für die Prognose. ${t.length ? `Heute: ${t.filter(e => +e.value >= 1).length}/${t.length}.` : ""}</div><button class="btn sm" id="vorabGo">Vorab-Test starten</button></div>`);
    $("#vorabGo").onclick = () => { go("training"); startMode("vorab"); }; }
  if (state.exam === "pmp" && !q) { $("#pfadList").insertAdjacentHTML("afterbegin", loopCard()); wireLoop(); }
}
$("#pfadSearch").addEventListener("input", () => renderPfad());
function ritaRef(l) { return ((l.refs || {}).rita || []).map(r => "Rita Kap. " + r.ch).join(", "); }
function renderExplore(q) {
  const E = D.eco || {}; const seen = LS.get("xlrte.explore", {});
  $("#pfadTitle").textContent = "Erkundung · PMP-Landkarte";
  $("#pfadSub").textContent = `ECO 2026 → PMBOK 8 (Vargas-Flow) → Rita 11th · ohne Wertung: zählt nicht für XP, Streak oder Prognose · ${Object.values(seen).filter(Boolean).length} / ${(E.los || []).length} Tasks angesehen`;
  const cov = {}; const byId = {}; items("pmp").forEach(i => { byId[i.id] = i; if (i.en) (cov[i.en] = cov[i.en] || { n: 0, a: 0, c: 0 }).n++; });
  EVENTS.forEach(e => { const i = e.kind === "attempt" && e.exam === "pmp" && byId[e.ref]; if (i && i.en && cov[i.en]) { cov[i.en].a++; if (+e.value === 1) cov[i.en].c++; } });
  const terms = glossary("pmp");
  const head = `<div class="card" style="margin-bottom:12px"><div class="label">PMBOK Guide 8 · 6 Prinzipien · 7 Performance-Bereiche · 40 Prozesse (nach Vargas)</div>
    <div class="small" style="margin:6px 0">${(E.pmbok8_principles || []).map(esc).join(" · ")}</div>
    <div class="row" style="flex-wrap:wrap;gap:6px">${(E.pmbok8_structure || []).map(a => `<span class="chip" title="${esc(a.processes.map(p => p.id + " " + p.name).join("\n"))}">${esc(a.area)} · ${a.processes.length}</span>`).join("")}</div></div>`;
  $("#pfadList").innerHTML = head + (E.categories || []).map(c => {
    const tasks = (E.los || []).filter(t => t.cat === c.id && (!q || JSON.stringify(t).toLowerCase().includes(q)));
    if (!tasks.length) return "";
    return `<details class="cat" open><summary><div><h3>${esc(c.id)} · ${esc(c.name)}</h3><div class="small muted">${c.weight} % · ${tasks.length} Tasks</div></div></summary><div class="body">`
      + tasks.map(t => { const r = t.refs || {}; const tt = terms.filter(g => (g.los || []).includes(t.id));
        return `<details class="explore"><summary><span class="id">${esc(t.id)}</span> ${esc(t.text)} <label class="tiny muted" style="float:right"><input type="checkbox" data-seen="${esc(t.id)}" ${seen[t.id] ? "checked" : ""}> angesehen</label></summary>
          <div class="small muted" style="margin:4px 0 8px">${esc(t.focus || "")}</div>
          <table class="small"><tr><th>Enabler (ECO)</th><th class="num">Fragen</th><th class="num">Abrufe</th><th class="num">Treffer</th></tr>${(t.enablers || []).map(e => { const c = cov[e.id] || {}; const q = c.a ? c.c / c.a : null; return `<tr><td>${esc(e.id)} ${esc(e.text)}</td><td class="num">${c.n || 0}</td><td class="num">${c.a || 0}</td><td class="num" style="${heatStyle(q, c.n || 0)}">${q === null ? (c.n ? "–" : "keine Frage") : Math.round(100 * q) + " %"}</td></tr>`; }).join("")}</table>
          <div class="small" style="margin-top:8px"><b>Rita 11th:</b> ${(r.rita || []).map(x => `Kap. ${x.ch} „${esc(x.title)}“ S. ${esc(x.pages)}`).join(" · ") || "—"}<br>
          <b>PMBOK 8:</b> ${(r.pmbok8 || []).map(esc).join(" · ") || "—"}${(r.pmbok8_ed || []).length ? " · Buch: " + r.pmbok8_ed.map(esc).join(" · ") : ""}<br>
          <b>PMBOK 7:</b> ${(r.pmbok7 || []).map(esc).join(" · ") || "—"}<br>
          <b>Kurs (PMI/Kursanbieter):</b> ${esc(courseRef(t.id)) || "—"}</div>
          ${courseNotesHTML(t.id)}
          ${tt.length ? `<div class="small" style="margin-top:6px"><b>Begriffe:</b> ${tt.map(g => `<span title="${esc(g.definition)}" style="text-decoration:underline dotted">${esc(g.term)}</span>`).join(", ")}</div>` : ""}</details>`; }).join("")
      + `</div></details>`;
  }).join("");
  $$("#pfadList [data-seen]").forEach(cb => { cb.onclick = ev => ev.stopPropagation(); cb.onchange = () => { const s = LS.get("xlrte.explore", {}); s[cb.dataset.seen] = cb.checked; LS.set("xlrte.explore", s); renderPfad(); }; });
}
function openLo(id) {
  const m = model(), l = loById(id), v = m.mm[id];
  const terms = glossary().filter(g => (g.los || []).includes(id));
  const its = items().filter(i => i.lo === id);
  const src = ((D.sources || {}).by_lo || {})[state.exam + ":" + id] || [];
  const wk = EVENTS.filter(e => e.kind === "workaround" && e.ref === id).slice(-1)[0];
  $("#drawer").innerHTML = `<div class="row" style="justify-content:space-between"><span class="label">Lernziel ${esc(id)} ${l.bl ? "· BL" + l.bl : ""}</span><button class="btn ghost sm" id="dClose">Schließen</button></div>
    <h2 style="margin:8px 0">${esc(l.text)}</h2>
    <div class="small muted">${l.topic_name ? esc(l.topic_name) + " · " : ""}${l.book ? "Buch §" + esc(l.book) : esc(l.focus || "")}${ritaRef(l) ? " · " + esc(ritaRef(l)) : ""}</div>
    ${(l.enablers || []).length ? `<div class="small" style="margin-top:8px">${l.enablers.map(e => `<div>· ${esc(e.text)}</div>`).join("")}</div>` : ""}
    <div class="kpis"><div class="kpi"><div class="v">${pct(v.m)}</div><div class="l">Beherrschung</div></div><div class="kpi"><div class="v">${fmt1(v.n)}</div><div class="l">Evidenz (gewichtet)</div></div><div class="kpi"><div class="v">${its.length}</div><div class="l">Fragen</div></div></div>
    <div class="row" style="margin:12px 0"><button class="btn acc sm" data-go="lo" data-lo="${esc(id)}">Dieses Lernziel drillen</button></div>
    ${terms.length ? `<h3 style="margin-top:14px">Begriffe (Glossar)</h3>` + terms.map(t => `<div class="copybox"><b>${esc(t.term)}</b><br><span class="small">${esc(t.definition)}</span></div>`).join("") : ""}
    ${wk ? `<h3 style="margin-top:14px">Deine Merkhilfe</h3><div class="copybox small">${esc((wk.meta || {}).text)}</div>` : ""}
    <h3 style="margin-top:14px">Aus deinen Unterlagen</h3>${src.length ? src.slice(-6).reverse().map(s => `<div class="copybox small"><span class="tiny muted">${esc(s.file)} · ${esc(s.date)} · ${esc(s.how)}</span><br>${esc(s.excerpt)}…</div>`).join("") : `<div class="small muted">Noch keine Auszüge. Lege Transkripte, Folien oder Notizen in <code>_xlrte/inbox/</code> – der tägliche Lauf ordnet sie Lernzielen zu.</div>`}`;
  $("#drawer").classList.add("on"); $("#scrim").classList.add("on");
  $("#dClose").onclick = closeDrawer;
}
function closeDrawer() { $("#drawer").classList.remove("on"); $("#scrim").classList.remove("on"); }
$("#scrim").onclick = closeDrawer;

/* ---------------------------------------------------------------- training */
function simCfg() { const ex = examCfg(), B = bank(); if (state.exam === "pmp") return { full: ex.questions || (D.eco || {}).questions || 180, fullMin: ex.sim_minutes || 240, mini: ex.mini_questions || 60, miniMin: ex.mini_minutes || 80 };
  return { full: ex.questions || B.questions || 40, fullMin: ex.sim_minutes || B.minutes || 60, mini: ex.mini_questions || 20, miniMin: ex.mini_minutes || 20 }; }
/* Prüfungskaliber: Einzelfrage mit Fragetext ab 40 Wörtern (Trainer: Ø ca. 55; Mastery Builder Ø 44); Fälle übt der Modus "Fallstudie", sie werden nie zerteilt. Kürzere Fragen unterschätzen das Lesetempo und machen die Falle "Signalwort" zu leicht. */
const KAL_MIN = 40;
function wordsOf(i) { return String(i.q || "").split(/\s+/).filter(Boolean).length; }
/* Abbildung zur Frage (Netzplan o. Ä.): nur eingebettete PNG-Data-URIs; heller Grund, damit die Vorlage auch im Dunkelmodus lesbar bleibt */
function figHTML(it) { return typeof it.fig === "string" && /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(it.fig) ? `<figure class="qfig" style="margin:12px 0;padding:12px;background:#fff;border-radius:10px;display:inline-block;max-width:100%"><img src="${it.fig}" alt="Abbildung zur Frage" style="display:block;width:min(100%,${Math.max(160, Math.min(+it.figw || 520, 720))}px);height:auto"></figure>` : ""; }
/* Rechenübung (type "num"): Zahleneingabe je Feld, Toleranz je Feld, danach Lösungsweg. Drill: keine Wertung in Reife/Mastery. */
function numParse(s) { const t = String(s || "").trim().replace(/\s/g, "").replace(",", "."); return t === "" || isNaN(+t) ? null : +t; }
function numOk(f, v) { return v !== null && Math.abs(v - f.answer) <= (f.tol || 0) + 1e-9; }
function numTable(rows) { return rows && rows.length ? `<table class="small" style="margin-top:10px">${rows.map((r, ri) => `<tr>${r.map(c => ri ? `<td>${esc(c)}</td>` : `<th>${esc(c)}</th>`).join("")}</tr>`).join("")}</table>` : ""; }
function numHTML(it, head) {
  return `<div class="qbox">${head}<div class="small muted" style="margin-top:6px">${esc(it.lo)} · ${esc(loById(it.lo).text)} · Rechenübung</div>
    <div class="qstem">${esc(it.q)}</div>${figHTML(it)}${numTable(it.table)}
    <div id="numf" style="margin-top:12px;display:grid;gap:8px;max-width:420px">${it.fields.map((f, k) => `<label class="row small" style="justify-content:space-between;gap:10px"><span>${esc(f.label)}${f.unit ? ` <span class="muted">(${esc(f.unit)})</span>` : ""}</span><input data-nf="${k}" inputmode="decimal" autocomplete="off" style="width:120px;text-align:right"></label>`).join("")}</div>
    <div class="row" id="conf" style="margin-top:10px"><span class="small muted">Antwort abgeben:</span><button class="btn" data-c="sure" disabled>Sicher <kbd>Enter</kbd></button><button class="btn ghost" data-c="unsure" disabled>Unsicher</button><button class="btn ghost" data-c="guess" disabled>Geraten</button></div>
    <div id="fb"></div></div>`;
}
function wireNum(it) {
  const ins = $$("#numf input"), ready = () => ins.every(x => numParse(x.value) !== null);
  ins.forEach(x => { x.oninput = () => $$("#conf button").forEach(b => b.disabled = !ready()); x.onkeydown = e => { if (e.key === "Enter" && ready() && !run.done) { e.preventDefault(); answerNum(it, "sure"); } }; });
  $$("#conf button").forEach(b => b.onclick = () => answerNum(it, b.dataset.c)); if (ins[0]) ins[0].focus();
}
function answerNum(it, conf) {
  if (!run || run.done) return; run.done = true;
  const vals = $$("#numf input").map(x => numParse(x.value)), hits = it.fields.map((f, k) => numOk(f, vals[k])), ok = hits.every(Boolean);
  addEvent("attempt", { ref: it.id, value: ok ? 1 : 0, exam: it.exam, meta: { conf, mode: run.mode, vals } });
  run.answers.push({ it, ok, conf, sel: vals });
  $$("#numf input").forEach((x, k) => { x.disabled = true; x.style.borderColor = hits[k] ? "var(--ok, #2e9d5b)" : "var(--no, #d0473a)"; });
  $$("#conf button").forEach(x => x.disabled = true);
  $("#fb").innerHTML = `<div class="feedback ${ok ? "ok" : "no"}"><b>${ok ? (conf === "guess" ? "Richtig – aber geraten" : "Richtig") : "Incident: noch nicht"}</b>
    <div class="small" style="margin:6px 0">${it.fields.map((f, k) => `${hits[k] ? "✓" : "✗"} ${esc(f.label)}: ${esc(String(f.answer))}${f.unit ? " " + esc(f.unit) : ""}${hits[k] ? "" : ` <span class="muted">(deine Eingabe: ${vals[k] === null ? "–" : esc(String(vals[k]))})</span>`}`).join("<br>")}</div>
    <div style="white-space:pre-line">${esc(it.why)}</div><div class="tiny muted" style="margin-top:6px">Lernziel ${esc(it.lo)} · ${esc(loById(it.lo).text)}</div></div>
    <div class="row" style="margin-top:10px"><button class="btn" id="next">Weiter <kbd>→</kbd></button></div>`;
  $("#next").onclick = () => { run.i++; renderRun(); }; $("#next").focus();
}
function rightText(it) { return it.type === "num" ? it.fields.map(f => `${f.label}: ${f.answer}${f.unit ? " " + f.unit : ""}`).join(" · ") : [].concat(it.answer).map(k => it.options[k]).join(" + "); }
function isKaliber(i) { return wordsOf(i) >= KAL_MIN && !i.case && i.type !== "num"; }
function setCaliber(mode) { const s = stemWords((D.items || []).filter(i => i.exam === state.exam && (MOCK_MODES[mode] || []).includes(i.set))); return s ? s.med : null; }
/* pure: 15 Kaliber-Fragen, schwache Tasks (Set von LO-Ids) zuerst, ungesehene vor gesehenen */
function kaliberPick(pool, weakLos, seen, rnd, n) {
  const mix = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const ok = pool.filter(isKaliber), rank = i => (weakLos.has(i.lo) ? 0 : 2) + (seen.has(i.id) ? 1 : 0);
  return [0, 1, 2, 3].flatMap(r => mix(ok.filter(i => rank(i) === r))).slice(0, n);
}
/* Pausen laut ECO 2026: Pause 1 nach dem Fallblock, Pause 2 etwa in der Mitte der Einzelfragen; ohne Fälle in Drittel */
function breakPoints(list) { const n = list.length, cc = list.filter(i => i.case).length; if (!cc) return [60, 120].filter(k => k < n); return [cc, cc + Math.round((n - cc) / 2)].filter(k => k > 0 && k < n); }
function calTag(ref) { const m = setCaliber(ref.replace(/^XLRTE-/, "").toLowerCase()); return m === null ? "" : ` · Fragen Ø ${m} Wörter ${m >= KAL_MIN ? "(Prüfungskaliber)" : "(kürzer als die Prüfung)"}`; }
/* Tagesschleife (PMP): Notebook = verstehen, Cockpit = abrufen, Prüfung = messen. Die nächste Messung ist die ungesehene mit dem größten Fragenkaliber. */
const MEASURES = [["m1a", "XLRTE-M1A", "Mock 1 · Teil A"], ["m1b", "XLRTE-M1B", "Mock 1 · Teil B"], ["m1c", "XLRTE-M1C", "Mock 1 · Teil C"], ["m3a", "XLRTE-M3A", "Mock 3 · Prüfungskaliber"], ["sz1", "XLRTE-SZ1", "Szenario-Set 1"], ["sz2", "XLRTE-SZ2", "Szenario-Set 2"], ["m2b", "XLRTE-M2B", "Mock 2 · Teil B"], ["m2c", "XLRTE-M2C", "Mock 2 · Teil C"], ["m2a", "XLRTE-M2A", "Fallen-Mock 2"]];
function nextMeasure() { return MEASURES.map((m, k) => [m, k]).filter(([m]) => !mockDone(m[1])).sort((a, b) => ((setCaliber(a[0][0]) || 0) >= KAL_MIN ? 0 : 1) - ((setCaliber(b[0][0]) || 0) >= KAL_MIN ? 0 : 1) || a[1] - b[1]).map(x => x[0])[0] || null; }
function kalPrompt(focus) { return `Based only on my sources (ECO 2026, PMBOK Guide 8, my learning journal and profile), quiz me with PMP scenario questions in exam caliber on the tasks ${focus}. One question at a time. Stem 45–60 words: my role, the situation, a trigger, one constraint, then the question (FIRST / NEXT / BEST). Four options of 8–20 words, similar length, exactly one best answer; every wrong option must exploit one typical trap (acting too early, skipping escalation, mixing agile and predictive, term confusion). Mix about 40 % predictive and 60 % agile or hybrid. Before revealing, ask me how sure I am (sure / unsure). Then give the PMI rationale for every option with the source page. After five questions list my mistakes as: task id, trap type, one-line takeaway.`; }
function loopCard() {
  const m = model(), dp = (C.day_plan || {})[TODAY] || {}, ex = examCfg(), d = dayDiff(TODAY, ex.target_date), nm = nextMeasure();
  const focus = (dp.focus_los || []).join(", ") || m.weak.slice(0, 3).map(w => w.lo.id).join(", ");
  const nk = (D.items || []).filter(i => i.exam === "pmp" && i.status !== "candidate" && isKaliber(i) && (i.drill || mockSeen(i))).length;
  const cal = nm ? setCaliber(nm[0]) : null;
  return `<div class="card" style="margin-bottom:12px" id="loopCard"><div class="label">Tagesschleife · Notebook → Cockpit → Prüfung${d >= 0 ? " · " + d + " Tage bis zum Termin" : ""}</div>
    <ol class="small" style="margin:8px 0 0;padding-left:18px;line-height:1.9">
      <li><b>Verstehen (Gemini Notebook):</b> Schwerpunkt ${esc(focus || "–")}. <button class="btn ghost sm" id="loopCp">Kaliber-Quiz-Prompt kopieren</button> <a class="btn ghost sm" href="${esc(C.notebook_url || "https://notebooklm.google.com")}" target="_blank" rel="noopener">Notebook öffnen</a><div class="tiny muted">Lernjournal vorher hochladen (Lernprofil oben), damit das Notebook deine Lücken kennt.</div></li>
      <li><b>Abrufen (Cockpit):</b> Kaliber-Drill mit den schwächsten Tasks zuerst. <button class="btn sm" id="loopKal">Starten</button><div class="tiny muted">${nk} Fragen im Prüfungskaliber im Pool (ab 40 Wörter). Fehler aus dem Notebook-Quiz gleich hier nachfassen.</div></li>
      <li><b>Messen (Prüfung):</b> ${nm ? `Nächste Messung: <b>${esc(nm[2])}</b>${cal !== null ? ` · Fragen Ø ${cal} Wörter` : ""}. <button class="btn sm" id="loopMeasure" data-m="${nm[0]}">Starten</button>` : "Alle Messungen absolviert – Vollmock zur Prüfungsuhrzeit."}<div class="tiny muted">Zählt erst, wenn ≥ 80 % beantwortet sind; Reife = zwei Messungen in Folge realistisch ≥ 75 %.</div></li>
    </ol></div>`;
}
function wireLoop() {
  const a = $("#loopCp"), b = $("#loopKal"), c = $("#loopMeasure"), dp = (C.day_plan || {})[TODAY] || {}, m = model();
  if (a) a.onclick = () => copy(kalPrompt((dp.focus_los || []).join(", ") || m.weak.slice(0, 3).map(w => w.lo.id).join(", ")));
  if (b) b.onclick = () => { go("training"); startMode("kal"); };
  if (c) c.onclick = () => { go("training"); startMode(c.dataset.m); };
}
function mockStatus(ref) { const e = mockDone(ref); return (e ? `absolviert: ${e.value}/${(e.meta || {}).of || 60}` : "ungesehen · einmalig") + calTag(ref); }
function modes() {
  const pmp = state.exam === "pmp", sc = simCfg();
  const dpv = (C.day_plan || {})[TODAY] || {}, vt = (dpv.focus_los || []);
  return [
    ...(pmp ? [["vorab", "Vorab-Test (3 Fragen)", "Pretest vor dem Kurstag: 3 Fragen zum heutigen Thema ohne Vorwissen. Fehler sind gewollt – die Auflösung zeigt, worauf du im Kurs achten sollst. Zählt nicht für Prognose, Wiederholung und Fehler-Management.", () => { const t = VORAB.filter(e => e.date === TODAY); return t.length ? `heute: ${t.filter(e => +e.value >= 1).length}/${t.length}` : vt.length ? "Tagesthema: " + vt.slice(0, 3).join(", ") + (vt.length > 3 ? " …" : "") : "kein Tagesthema"; }]] : []),
    ["due", "Fällige Wiederholungen", "Leitner-System: Was heute fällig ist, zuerst.", () => dueList().length + " fällig"],
    ["hyper", "Sicher & falsch", "Fehler, bei denen du dir sicher warst – nach der Korrektur prägen sie sich am stärksten ein (Hyperkorrektur). Mit kurzer Reflexion.", () => hyperItems().length + " offen"],
    ["weak", "Schwachstellen-Drill", "15 Fragen aus den Lernzielen mit der größten gewichteten Lücke – „sicher & falsch“ zuerst.", () => "Top-5 Lücken"],
    ...(pmp ? [["kal", "Kaliber-Drill (15)", "Nur Einzelfragen im Prüfungskaliber (Fragetext ab 40 Wörtern; Fälle übst du unter Fallstudie), schwächste Tasks zuerst, Ungesehenes vor Gesehenem. Mit Sofort-Feedback. Übt Lesetempo und Fallen so, wie der Trainer die echte Prüfung beschreibt.", () => { const n = (D.items || []).filter(i => i.exam === "pmp" && i.status !== "candidate" && isKaliber(i) && !i.drill && mockSeen(i)).length; return n + " Kaliber-Fragen offen im Pool"; }]] : []),
    ["mini", "Mini-Mock (20)", "Blueprint-gewichtet, mit Sofort-Feedback.", () => "≈ 15 Min"],
    pmp ? ["sim", `Vollsimulation (${sc.full} / ${sc.fullMin} Min)`, "Wie die echte PMP-Prüfung: Fallstudien-Block zuerst, zwei optionale 10-Min-Pausen, kein Zurück, kein Feedback bis zum Ende.", () => "Prüfungsmodus"]
        : ["sim", `Simulation (${sc.full} / ${sc.fullMin} Min)`, "Wie die echte Prüfung: kein Feedback bis zum Ende, Zeitlimit.", () => "Prüfungsmodus"],
    ...(!pmp && (D.items || []).some(i => i.exam === state.exam && /^S[1-4]$/.test(i.set || "")) ? [
      ["s1", "Schattenprüfung S1 (40 / 60 Min)", "40 ungesehene Fragen im Stil der offiziellen Musterprüfungen: Szenarien, HAUPTZWECK / AM BESTEN, Geschwister-Begriffe als Optionen, exakte Kategorie- und Bloom-Verteilung. Erster blinder Härtetest.", () => { const e = s1Event(); return e ? `absolviert: ${e.value}/${(e.meta || {}).of || 40}` : "ungesehen · einmalig"; }],
      ["s2", "Schattenprüfung S2 (40 / 60 Min)", "40 NEUE ungesehene Fragen im PeopleCert-Formprofil. Zweiter Härtetest zur Absicherung stabiler Werte vor SP1 und der Terminbuchung.", () => { const e = s2Event(); return e ? `absolviert: ${e.value}/${(e.meta || {}).of || 40}` : "ungesehen · einmalig"; }],
      ["s3", "Schattenprüfung S3 (40 / 60 Min)", "40 weitere NEUE Fragen im PeopleCert-Formprofil, gewichtet auf deine SP1-Fehlerbilder. Letzter Trockenlauf vor SP2; Lernziel-Zeile ist ausgeblendet.", () => { const e = s3Event(); return e ? `absolviert: ${e.value}/${(e.meta || {}).of || 40}` : "ungesehen · einmalig"; }],
      ["s4", "Schattenprüfung S4 · SP-Form (40 / 60 Min)", "40 neue Fragen im Formprofil der offiziellen Musterprüfungen: kurze Stämme, kurze Geschwister-Optionen, Unterscheidung ähnlicher Begriffe. Näher an SP1/SP2 als S1–S3; Lernziel-Zeile ist ausgeblendet.", () => { const e = s4Event(); return e ? `absolviert: ${e.value}/${(e.meta || {}).of || 40}` : "ungesehen · einmalig"; }]
    ] : []),
    ...(pmp ? [
      ["fall", "Fallstudie · Fragen zuerst (ca. 5 Fragen)", "Eine Fallstudie mit mehreren Fragen zu einem Text, geübt mit der Trainer-Taktik: erst die Fragen überfliegen (Suchauftrag), dann den Fall lesen, dann antworten. Bevorzugt einen Fall, den du noch nicht gesehen hast. Mit Rückmeldung nach jeder Frage; zählt als normale Übung.", () => ""],
      ["m1a", "Mock 1 · Teil A (60 / 80 Min)", "60 ungesehene Fragen nach ECO-Blueprint (People 33 / Process 41 / Business Environment 26), 40 % predictiv, 60 % agil/hybrid, inkl. Mehrfachauswahl. Kein Feedback bis zum Ende, Lernziel-Zeile ausgeblendet. Der Ergebnis-Wert zählt für die Prognose, weil die Fragen neu sind.", () => mockStatus("XLRTE-M1A")],
      ["m1b", "Mock 1 · Teil B (60 / 80 Min)", "60 weitere ungesehene Fragen im gleichen Blueprint, andere Szenarien. Zweiter Messpunkt.", () => mockStatus("XLRTE-M1B")],
      ["m1c", "Mock 1 · Teil C (60 / 80 Min)", "Dritter Teil von Mock 1: weitere 60 ungesehene Fragen im gleichen Blueprint.", () => mockStatus("XLRTE-M1C")],
      ["m2a", "Fallen-Mock 2 (60 / 80 Min)", "60 neue ungesehene Fragen, gezielt auf die typischen Prüfungsfallen gebaut (voreiliges Handeln, Eskalation, Agil/Predictive, Begriffe, Rechnen, Rollen). Jede falsche Option zielt auf eine bestimmte Falle; nach dem Lauf zeigt dir „Fallen dieser Runde“, in welche du gefallen bist.", () => mockStatus("XLRTE-M2A")],
      ["m3a", "Mock 3 · Prüfungskaliber (60 / 80 Min)", "60 neue ungesehene Fragen mit langen Szenario-Fragetexten (45–60 Wörter), so wie der Trainer die Prüfung beschreibt: Rolle, Lage, Auslöser, eine Einschränkung, dann die Frage. Jede falsche Option zielt auf eine Falle. Ungesehene Messung, zählt in die realistische Reife.", () => mockStatus("XLRTE-M3A")],
      ["sz1", "Szenario-Set 1 · PMBOK 8 (60 / 80 Min)", "60 neue ungesehene Praxisszenarien aus PMBOK 8 (Governance, Scope, Termin, Finanzen, Stakeholder, Ressourcen, Risiko) mit drei neuen Fallstudien zu je 5 Fragen (Pharma-Werk, Stadtportal, verteilte App). Jede falsche Option zielt auf eine Falle. Ungesehene Messung, zählt in die realistische Reife.", () => mockStatus("XLRTE-SZ1")],
      ["sz2", "Szenario-Set 2 · PMBOK 8 (60 / 80 Min)", "60 weitere ungesehene Praxisszenarien aus PMBOK 8 mit mehr Mehrfachauswahl und Rechenaufgaben und drei neuen Fallstudien (Krankenhaus-Bau, Händler-ERP, KI-Schadenassistent). Jede falsche Option zielt auf eine Falle. Ungesehene Messung, zählt in die realistische Reife.", () => mockStatus("XLRTE-SZ2")],
      ["m2b", "Mock 2 · Teil B (60 / 80 Min)", "60 neue ungesehene Fragen nach ECO-Blueprint (33 / 41 / 26, ca. 40 % predictiv), mit drei Fallstudien zu je 5 Fragen (Rechenzentrum, Banking-App, E-Learning-Plattform). Teil von Vollmock 2. Zählt als eigene Messung mit Abschlag.", () => mockStatus("XLRTE-M2B")],
      ["m2c", "Mock 2 · Teil C (60 / 80 Min)", "60 weitere ungesehene Fragen nach ECO-Blueprint mit mehr Mehrfachauswahl und Rechenaufgaben und drei Fallstudien (Windpark, Termin-Plattform, ERP-Einführung). Teil von Vollmock 2.", () => mockStatus("XLRTE-M2C")],
      ["m2", "Vollmock 2 (180 / 240 Min)", "Alle drei Teile von Mock 2 (Fallen-Mock A, B, C) zusammen wie die echte Prüfung: 180 Fragen, zwei optionale 10-Min-Pausen nach Frage 60 und 120, mit Fallstudien. Plane ihn zur Uhrzeit deines Prüfungstermins ein. Zählt als eigene Messung mit Abschlag.", () => mockStatus("XLRTE-M2")],
      ["mbp", "PMI Übungsfragen · People (38)", "Offizielle PMI-Mastery-Builder-Fragen zur Domäne People (Tasks P.1–P.8) mit Begründung zu jeder Option. Einmalig ungesehen; danach im Übungspool. Zählt als eigene Messung mit Abschlag. Achtung: Die richtige Option ist hier in ca. 56 % die längste, der Rohwert fällt also zu hoch aus.", () => mockStatus("XLRTE-MBP")],
      ["mbr", "PMI Übungsfragen · Process (49)", "Offizielle PMI-Mastery-Builder-Fragen zur Domäne Process (Tasks PR.1–PR.10) mit Begründung zu jeder Option. Einmalig ungesehen; danach im Übungspool.", () => mockStatus("XLRTE-MBR")],
      ["mbb", "PMI Übungsfragen · Business Environment (34)", "Offizielle PMI-Mastery-Builder-Fragen zur Domäne Business Environment (Tasks BE.1–BE.8) mit Begründung zu jeder Option. Einmalig ungesehen; danach im Übungspool.", () => mockStatus("XLRTE-MBB")],
      ["m1", "Vollmock 1 (180 / 240 Min)", "Alle drei Teile zusammen wie die echte Prüfung: 180 Fragen gemischt, zwei optionale 10-Min-Pausen nach Frage 60 und 120, kein Zurück. Generalprobe; enthält bereits absolvierte Teile nur, wenn du sie vorher einzeln gemacht hast.", () => mockStatus("XLRTE-M1")]
    ] : []),
    ...(pmp ? [["simmini", `Mini-Sim (${sc.mini} / ${sc.miniMin} Min)`, "Ein Drittel der Prüfung unter Zeitdruck – Domänengewichte wie im ECO.", () => "Prüfungsmodus"]] : []),
    ["cards", pmp ? "Begriffskarten" : "Glossarkarten", pmp ? "Formeln, Vertragsarten, agile Artefakte, Modelle – aktiv abrufen." : "Offizielle Definitionen aktiv abrufen – BL1 ist 40 % der Prüfung.", () => glossary().length + " Begriffe"],
    ...(pmp ? [["cardsmn", "Begriffskarten mit Merkhilfe", "Nur Karten mit Kurzfassung und Eselsbrücke oder eigener Notiz, schwächste Karten zuerst.", () => glossary().filter(hasHint).length + " Karten"]] : []),
    ...(pmp ? drillSets().map(([id, n, done]) => ["drill:" + id, id === "TRC" ? `Rechenübungen (${n})` : id === "GEN" ? `Neue Rechenübungen von heute (${n})` : id.startsWith("WM") ? `Übungsbuch ${id} (${n})` : `Trainer-Übung ${id} (${n})`, id.startsWith("WM") ? "Wissensfragen aus dem Übungsbuch „PMP Exam Prep 2025 – 1000 Practice Questions“ (Wiman): Prozesse, Dokumente, Begriffe im PMBOK-6-Stil, kurz und ohne Prüfungskaliber. Gut zum Begriffe-Festigen; bei Abweichung gelten PMBOK 8 und der ECO 2026, einzelne Schlüssel sind diskutabel. Keine Wertung in der Reife-Messung." : id === "TRC" ? "Netzplan, kritischer Pfad, Puffer, PERT und Knotenwerte mit Zahleneingabe und Lösungsweg (Übungen 301–308 der 333-Sammlung, Abbildungen aus der Quelle). Keine Wertung in der Reife-Messung." : id === "TR1" ? "Die Fragen aus dem Kurs-Dokument des Trainers, mit markiertem Schlüssel. Normale Übungsfragen: sofortiges Feedback, keine Wertung in der Reife-Messung, kein Beleg für die Task-Beherrschung." : "Übungsfragen aus der 333-Sammlung (Studienbuch-Stil, ECO-2021-Stand; bei Abweichung gilt PMBOK 8 und der ECO 2026). Normale Übungsfragen: sofortiges Feedback, keine Wertung in der Reife-Messung.", () => done ? `${done} beantwortet` : "ungeübt"]) : []),
    ["new", "Neue Fragen prüfen", "Vom täglichen Lauf erzeugte Kandidaten: nutzen und bewerten.", () => openCands(items(), EVENTS).length + " offen"],
    ...(items().some(i => i.set === "GEN") ? [["gen", "Neue Übungen von heute", "Jeden Tag neu und deterministisch aus den Begriffskarten deines Pakets erzeugt: Begriff zur Beschreibung und umgekehrt, schwächste Lernziele zuerst.", () => items().filter(i => i.set === "GEN").length + " neu"]] : [])
  ].filter(m => !MOCK_MODES[m[0]] || (D.items || []).some(i => i.exam === state.exam && MOCK_MODES[m[0]].includes(i.set)));
}
const isSim = mode => mode === "sim" || mode === "simmini" || mode === "s1" || mode === "s2" || mode === "s3" || mode === "s4" || mode === "sp1" || mode === "sp2" || isMock(mode);
function trapPanelHTML() {
  const T = D.traps || {}, tax = T.taxonomy || [];
  if (state.exam !== "pmp" || !tax.length) return "";
  const sw = `<label class="row small" style="gap:8px;align-items:center"><input type="checkbox" id="trapSwitch" ${trapsOn() ? "checked" : ""}> Fallen-Hinweise anzeigen</label>`;
  if (!trapsOn()) return sw;
  const st = trapStats(EVENTS, "pmp", TODAY, items("pmp"), T);
  const rows = trapRank(st, tax).map(t => { const s = st[t.id];
    const q = s.status === "ok" ? pct(s.quote) : "zu wenig Daten", tr = s.trend === null || s.trend === undefined ? "–" : (s.trend >= 0 ? "▲ +" : "▼ ") + Math.round(s.trend * 100) + " Pp";
    return `<tr><td><b>${esc(t.name)}</b><div class="tiny muted">${esc(t.rule)}</div></td><td class="num">${s.n}</td><td class="num">${q}</td><td class="num">${s.sure_wrong}</td><td class="num">${tr}</td><td><button class="btn sm" data-trap="${esc(t.id)}">Drillen</button></td></tr>`; }).join("");
  return `${sw}<details open class="card" style="margin-top:8px"><summary><b>Fallen-Radar</b> <span class="tiny muted">Quote, „sicher &amp; falsch“ und Trend je Prüfungsfalle · Rangfolge nach gewichteter Lücke</span></summary>
    <table style="margin-top:8px"><tr><th>Falle</th><th class="num">Versuche</th><th class="num">Quote</th><th class="num">Sicher &amp; falsch</th><th class="num">Trend</th><th></th></tr>${rows}</table></details>`;
}
function renderTrapPanel() {
  const el = $("#trapPanel"); if (!el) return; el.innerHTML = trapPanelHTML();
  const sw = $("#trapSwitch"); if (sw) sw.onchange = () => { addEvent("setting", { ref: "ui.traps", value: sw.checked }); renderTrapPanel(); };
  $$("#trapPanel [data-trap]").forEach(b => b.onclick = () => startMode("trap:" + b.dataset.trap));
}
function drillSets() { const c = {}; (D.items || []).forEach(i => { if (i.exam === "pmp" && i.drill) c[i.drill] = (c[i.drill] || 0) + 1; }); const seen = new Set(EVENTS.filter(e => e.kind === "attempt").map(e => e.ref)); return Object.keys(c).sort().map(id => [id, c[id], (D.items || []).filter(i => i.drill === id && seen.has(i.id)).length]); }
function trapDrillList(id) {
  const tag = (D.traps || {}).items || {}, hs = new Set(hyperItems().map(i => i.id)), last = {};
  EVENTS.forEach(e => { if (e.kind === "attempt" && e.exam === "pmp") last[e.ref] = +e.value >= 1 ? 1 : 0; });
  const rank = i => hs.has(i.id) ? 0 : last[i.id] === 0 ? 1 : last[i.id] === undefined ? 2 : 3;
  return shuffle(items("pmp").filter(i => (tag[i.id] || []).includes(id))).sort((a, b) => rank(a) - rank(b)).slice(0, 15);
}
/* Training-Reiter: Hierarchie und Relevanz. Rein (testbar): list = [[key, title, desc, countText]], ctx = {pmp, days, light, due, hyper, vorabOpen, candOpen}.
   Stufe nach Prüfungsnähe und Reife: aufbau (> 28 Tage oder rote Ampel bei > 14 Tagen), messen (11–28), endspurt (≤ 10). */
const TRAIN_GROUPS = { taeglich: "Täglich festigen", gezielt: "Gezielt üben", messen: "Messen mit ungesehenen Sätzen", sim: "Prüfungssimulation", sonst: "Weitere" };
const TRAIN_ORDER = { aufbau: ["taeglich", "gezielt", "messen", "sim", "sonst"], messen: ["messen", "taeglich", "gezielt", "sim", "sonst"], endspurt: ["sim", "messen", "taeglich", "gezielt", "sonst"] };
function trainGroupOf(k) {
  if (["vorab", "due", "hyper", "weak", "kal", "mini", "cards", "cardsmn"].includes(k)) return "taeglich";
  if (k === "fall" || k.startsWith("drill:")) return "gezielt";
  if (["sim", "simmini", "m1", "m2"].includes(k)) return "sim";
  if (["new"].includes(k)) return "sonst";
  return "messen";
}
function trainStage(days, light) { if (days === null || days === undefined || isNaN(days)) return "aufbau"; if (days <= 10) return "endspurt"; if (days <= 28 && !(light === "red" && days > 14)) return "messen"; return "aufbau"; }
function trainPlan(list, ctx) {
  const stage = trainStage(ctx.days, ctx.light), d = ctx.days === null || ctx.days === undefined ? 99 : ctx.days;
  const cards = list.map(([k, t, desc, n]) => {
    const txt = String(n || ""), done = /absolviert/.test(txt), fresh = /ungesehen/.test(txt);
    let sc = 0, why = "";
    const up = (v, w) => { if (v > sc) { sc = v; why = w; } };
    if (k === "due" && ctx.due > 0) up(100, ctx.due + " Wiederholungen fällig");
    if (k === "hyper" && ctx.hyper > 0) up(80, ctx.hyper + " Fehler mit hoher Sicherheit offen");
    if (k === "vorab" && ctx.vorabOpen) up(90, "Pretest zum Tagesthema steht aus");
    if (k === "new" && ctx.candOpen > 0) up(30, ctx.candOpen + " neue Fragen warten auf Prüfung");
    if (k === "weak") up(45, "größte gewichtete Lücke zuerst");
    if (k === "kal") up(40, "Fragetexte im Prüfungskaliber");
    if (fresh && trainGroupOf(k) === "messen") up(stage === "aufbau" ? 20 : 70, stage === "aufbau" ? "ungesehene Messung (später sinnvoller)" : "ungesehener Satz: ehrliche Messung für die Reife");
    if ((k === "m1" || k === "m2") && !done) up(d <= 10 ? 85 : d <= 28 ? 35 : 5, d <= 10 ? "Generalprobe in der Endphase" : "Generalprobe erst gegen Ende");
    if (k === "sim" && !done) up(d <= 7 ? 75 : 10, d <= 7 ? "Prüfungsmodus in der letzten Woche" : "Prüfungsmodus später");
    if (k === "fall") up(stage === "aufbau" ? 50 : 35, "Fallstudien nach der Trainer-Taktik");
    if (k === "drill:TRC") { sc = -40; why = "ECO 2026: laut Trainer kaum Rechenfragen"; }
    if (done) { sc -= 50; why = "bereits absolviert"; }
    return { k, t, desc, n: txt, score: sc, why, done, group: trainGroupOf(k) };
  });
  const order = TRAIN_ORDER[stage];
  const groups = order.map((g, gi) => ({ id: g, title: TRAIN_GROUPS[g], open: gi < 2, cards: cards.filter(c => c.group === g).sort((a, b) => b.score - a.score) })).filter(g => g.cards.length);
  const top = cards.filter(c => c.score >= 40 && !c.done).sort((a, b) => b.score - a.score).slice(0, 4);
  return { stage, groups, top };
}
function trainCardHTML(c, reason) {
  return `<div class="card"><div class="label">${c.n}</div><h3 style="margin:4px 0 6px">${c.t}</h3><div class="small muted" style="min-height:40px">${c.desc}</div>${reason && c.why ? `<div class="small" style="margin-top:6px"><b>Warum jetzt:</b> ${esc(c.why)}</div>` : ""}<button class="btn sm" data-go="${c.k}" style="margin-top:10px">Starten</button></div>`;
}
const TRAIN_STAGE_TXT = { aufbau: "Aufbau: Wissen festigen, Lücken schließen, Messungen erst später", messen: "Messphase: ungesehene Sätze liefern die ehrlichen Werte", endspurt: "Endspurt: Prüfungsmodus, Timing und Fallen" };
function renderTrainingMenu() {
  const ex = examCfg(), days = ex.target_date ? dayDiff(TODAY, ex.target_date) : null, pmp = state.exam === "pmp";
  const light = pmp ? realityLight(realityMeasures(EVENTS, "pmp", examCfg("pmp").reality_discount_pp || { own: 10, official: 5 }), examCfg("pmp").target_pct || 75).light : null;
  const vt = VORAB.filter(e => e.date === TODAY), dpv = (C.day_plan || {})[TODAY] || {};
  const plan = trainPlan(modes().map(([k, t, d, n]) => [k, t, d, n()]), { days, light, due: dueList().length, hyper: hyperItems().length, vorabOpen: pmp && !vt.length && (dpv.focus_los || []).length > 0, candOpen: openCands(items(), EVENTS).length });
  const head = `<div class="small muted" style="margin-bottom:8px">${esc(TRAIN_STAGE_TXT[plan.stage])}${days !== null ? ` · ${days} Tage bis ${esc(ex.name || "Prüfung")}` : ""}</div>`;
  const top = plan.top.length ? `<h3 style="margin:6px 0">Heute für dich</h3><div class="grid g3">${plan.top.map(c => trainCardHTML(c, true)).join("")}</div>` : "";
  const grp = plan.groups.map(g => `<details ${g.open ? "open" : ""} style="margin-top:14px"><summary style="cursor:pointer;font-weight:600">${esc(g.title)} <span class="small muted">(${g.cards.length})</span></summary><div class="grid g3" style="margin-top:8px">${g.cards.map(c => trainCardHTML(c, false)).join("")}</div></details>`).join("");
  $("#modeCards").innerHTML = head + top + grp;
  renderTrapPanel(); renderCandPanel();
}
function renderCandPanel() {
  const el = $("#candPanel"); if (!el) return; const list = state.exam === "pmp" ? openCands(items("pmp"), EVENTS) : openCands(items(), EVENTS);
  el.innerHTML = candPanelHTML(list) + (state.exam === "pmp" ? paceTrendHTML(EVENTS) : "");
  const rv = keep => { $$("#candPanel [data-cand]").forEach(cb => { const id = cb.dataset.cand; addEvent("review", { ref: id, value: (keep === "all" || cb.checked) ? 1 : 0, exam: state.exam }); }); toast("Gespeichert"); renderTrainingMenu(); };
  if ($("#candOk")) $("#candOk").onclick = () => rv("sel"); if ($("#candAll")) $("#candAll").onclick = () => rv("all"); if ($("#candDrill")) $("#candDrill").onclick = () => startMode("new");
}
let run = null;
/* why-texts in the bank cite ORIGINAL option letters; options are shuffled on display → remap to displayed letters */
function whyMapped(why, order) {
  if (!order || !why) return why || "";
  const L = "ABCDEF", disp = k => L[order.indexOf(k)] || L[k];
  return why.replace(/(^|[\s(,;.:„])([A-E])(?=\s*(?:=|ist\b|beschreibt\b|ähnelt\b|wäre\b))/g, (m, p, c) => p + disp(L.indexOf(c)))
            .replace(/(Glossar-Definition\s+|Option\s+)([A-E])\b/g, (m, p, c) => p + disp(L.indexOf(c)));
}
function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
/* hypercorrection: items whose last "sure" answer was wrong and not answered correctly since — newest first */
function hyperQueue(events, exam, ids) {
  const r = {};
  events.forEach(e => { if (e.kind !== "attempt" || e.exam !== exam || !ids.has(e.ref)) return; const x = r[e.ref] = r[e.ref] || {}; const ts = e.ts || e.date;
    if (+e.value >= 1) { if (!x.ok || ts > x.ok) x.ok = ts; } else if ((e.meta || {}).conf === "sure") { if (!x.sw || ts > x.sw) x.sw = ts; } });
  return Object.keys(r).filter(k => r[k].sw && !(r[k].ok && r[k].ok > r[k].sw)).sort((a, b) => r[b].sw.localeCompare(r[a].sw));
}
/* calibration: how often is "sure" actually right? */
function calibration(events, exam, since) {
  const s = events.filter(e => e.kind === "attempt" && e.exam === exam && (e.meta || {}).conf === "sure" && e.date >= since);
  const ok = s.filter(e => +e.value >= 1).length; return { n: s.length, ok, rate: s.length ? ok / s.length : null };
}
/* Fallen-Radar (Spiegel von scripts/trapstats.py; Fixture tests/trap_stats_fixture.json) */
function trapStats(events, exam, today, items, traps, hl = 10) {
  const tags = (traps || {}).items || {}, lures = (traps || {}).lures || {};
  const vis = new Set(items.filter(i => i.exam === exam).map(i => i.id));
  const acc = {}; ((traps || {}).taxonomy || []).forEach(t => acc[t.id] = { n: 0, w: 0, c: 0, sw: 0, rn: 0, rc: 0, pn: 0, pc: 0, wp: 0, lp: 0 });
  const day = s => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10));
  events.forEach(e => {
    if (e.kind !== "attempt" || e.exam !== exam || !vis.has(e.ref)) return;
    const ts = tags[e.ref] || []; if (!ts.length) return;
    const m = e.meta || {}, age = Math.max(0, Math.round((day(today) - day(e.date)) / 864e5)), val = +e.value || 0;
    const c = val >= 1 ? (m.conf === "guess" ? .5 : 1) : 0, ww = Math.pow(.5, age / hl);
    ts.forEach(t => {
      const a = acc[t]; if (!a) return;
      a.n++; a.w += ww; a.c += ww * c;
      if (val < 1 && m.conf === "sure") a.sw++;
      if (age <= 6) { a.rn++; a.rc += c; } else if (age <= 13) { a.pn++; a.pc += c; }
      if (val < 1 && m.pick !== undefined && m.pick !== null && lures[e.ref]) { a.wp++; if (lures[e.ref][String(m.pick)] === t) a.lp++; }
    });
  });
  const r4 = x => x === null ? null : Math.round(x * 1e4) / 1e4, out = {};
  Object.keys(acc).forEach(t => {
    const a = acc[t], q = a.w ? a.c / a.w : null;
    out[t] = { n: a.n, quote: r4(q), sure_wrong: a.sw, trend: a.rn >= 5 && a.pn >= 5 ? r4(a.rc / a.rn - a.pc / a.pn) : null,
      status: a.n >= 5 ? "ok" : "zu wenig Daten", gap: q === null ? 0 : r4(a.w * (1 - q)), lure_share: a.wp ? r4(a.lp / a.wp) : null };
  });
  return out;
}
function trapRank(st, tax) {
  return tax.slice().sort((a, b) => { const x = st[a.id], y = st[b.id], ox = x.status === "ok" ? 0 : 1, oy = y.status === "ok" ? 0 : 1; return ox - oy || (ox === 0 ? y.gap - x.gap : y.n - x.n); });
}
function trapsOn() { const v = settings()["ui.traps"]; return v === undefined || isTrue(v); }
function trapName(id) { const t = (((D.traps || {}).taxonomy) || []).find(x => x.id === id); return t ? t.name : id; }
function trapRule(id) { const t = (((D.traps || {}).taxonomy) || []).find(x => x.id === id); return t ? t.rule : ""; }
function hyperItems() { const ids = new Set(items().map(i => i.id)); const byId = {}; items().forEach(i => byId[i.id] = i); return hyperQueue(EVENTS, state.exam, ids).map(k => byId[k]); }
function shuffleWith(a, rnd) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
/* pure: domain quotas, whole cases first (never split), unseen items preferred. pool: [{id, cat, case?}] */
function simPick(pool, cats, n, opts) {
  const rnd = opts.rnd || Math.random, seen = opts.seen || new Set(), caseFirst = opts.caseFirst || 0;
  const quota = {}; cats.forEach(c => quota[c.id] = Math.round(n * c.weight / 100));
  const diff = n - Object.values(quota).reduce((s, v) => s + v, 0); const big = cats.slice().sort((a, b) => b.weight - a.weight)[0]; if (big) quota[big.id] += diff;
  const block = [];
  if (caseFirst > 0) {
    const byCase = {}; pool.filter(i => i.case).forEach(i => (byCase[i.case] = byCase[i.case] || []).push(i));
    for (const cid of shuffleWith(Object.keys(byCase), rnd)) { if (block.length >= caseFirst || block.length + byCase[cid].length > n) break; byCase[cid].forEach(i => { block.push(i); quota[i.cat] = (quota[i.cat] || 0) - 1; }); }
  }
  const rest = [], free = pool.filter(i => !i.case);
  const order = arr => shuffleWith(arr.filter(i => !seen.has(i.id)), rnd).concat(shuffleWith(arr.filter(i => seen.has(i.id)), rnd));
  cats.forEach(c => rest.push(...order(free.filter(i => i.cat === c.id)).slice(0, Math.max(0, quota[c.id] || 0))));
  if (block.length + rest.length < n) { const used = new Set(rest.map(i => i.id)); rest.push(...order(free.filter(i => !used.has(i.id))).slice(0, n - block.length - rest.length)); }
  return { list: block.concat(shuffleWith(rest, rnd)).slice(0, n), caseCount: block.length };
}
function blueprintSample(n, caseFirst = 0) {
  if (state.exam === "pmp") {
    const seen = new Set(EVENTS.filter(e => e.kind === "attempt" && e.exam === "pmp").map(e => e.ref));
    const pool = items().filter(i => i.status !== "candidate").map(i => Object.assign({}, i, { cat: loById(i.lo).cat }));
    const r = simPick(caseFirst ? pool : pool.filter(i => !i.case), (bank().categories || []), n, { caseFirst, seen });
    blueprintSample.caseCount = r.caseCount; return r.list;
  }
  blueprintSample.caseCount = 0;
  const m = model(); const pool = items().filter(i => i.status !== "candidate"); const out = [];
  m.B.categories.forEach(c => {
    const k = Math.max(c.weight >= 5 ? 1 : 0, Math.round(n * c.weight / 100));
    const catPool = pool.filter(i => (loById(i.lo).cat) === c.id);
    const bl2Pool = shuffle(catPool.filter(i => (i.bl || 1) === 2));
    const bl1Pool = shuffle(catPool.filter(i => (i.bl || 1) === 1));
    const targetBL2 = Math.min(bl2Pool.length, Math.round(k * 0.6));
    const targetBL1 = Math.min(bl1Pool.length, k - targetBL2);
    let chosen = bl2Pool.slice(0, targetBL2).concat(bl1Pool.slice(0, targetBL1));
    if (chosen.length < k) {
      const remaining = shuffle(catPool.filter(i => !chosen.includes(i)));
      chosen = chosen.concat(remaining.slice(0, k - chosen.length));
    }
    out.push(...chosen);
  });
  return shuffle(out).slice(0, n);
}
function startMode(mode, lo) {
  const m = model(); let list = [], cards = false;
  if (mode === "due") { const d = new Set(dueList()); const hs = new Set(hyperItems().map(i => i.id)); list = items().filter(i => d.has(i.id)).sort((a, b) => hs.has(b.id) - hs.has(a.id)); const gc = glossary().filter(g => d.has(g.id)); if (!list.length && gc.length) { cards = true; list = gc; } else if (!list.length) { toast("Nichts fällig – starte einen Schwachstellen-Drill"); mode = "weak"; } }
  if (mode === "hyper") { list = hyperItems(); if (!list.length) { toast("Keine offenen „sicher & falsch“-Fehler – starte einen Schwachstellen-Drill"); mode = "weak"; } }
  if (mode === "weak") { const ids = new Set(m.weak.map(w => w.lo.id)); const hy = hyperItems().slice(0, 5); const hs = new Set(hy.map(i => i.id));
    const ms = masteredIds(EVENTS); list = hy.concat(shuffle(items().filter(i => ids.has(i.lo) && !hs.has(i.id) && !ms.has(i.id)))).slice(0, 15); if (list.length < 8) list = list.concat(blueprintSample(15 - list.length)); }
  if (mode === "kal") { const ids = new Set(m.weak.map(w => w.lo.id)), seen = new Set(EVENTS.filter(e => e.kind === "attempt" && e.exam === "pmp").map(e => e.ref)), rej = rejected(), pool = new Set(items().map(i => i.id));
    list = kaliberPick((D.items || []).filter(i => i.exam === "pmp" && i.status !== "candidate" && !rej.has(i.id) && (i.drill || pool.has(i.id))), ids, seen, Math.random, 15); if (!list.length) { toast("Noch keine Kaliber-Fragen verfügbar – Mock 3 oder die neuen Tagesfragen zuerst"); return; } }
  if (mode === "lo") { const all = items().filter(i => i.lo === lo), ms = masteredIds(EVENTS), open = all.filter(i => !ms.has(i.id)); list = shuffle(open.length >= 5 ? open : all); }
  if (mode === "mini") list = blueprintSample(20);
  if (mode === "fall") { const seenIds = new Set(EVENTS.filter(e => e.kind === "attempt" && e.exam === "pmp").map(e => e.ref)); list = pickCaseRun(D.cases || [], items("pmp"), seenIds); if (!list.length) { toast("Keine Fallstudie verfügbar"); return; } }
  if (mode === "vorab") { const tk = ((C.day_plan || {})[TODAY] || {}).focus_los || []; const seen = new Set(EVENTS.concat(VORAB).filter(e => e.kind === "attempt" && e.exam === "pmp").map(e => e.ref));
    list = vorabPick(items().filter(i => i.status !== "candidate"), tk, seen, Math.random, 3); if (!list.length) { toast("Für heute ist kein Tagesthema hinterlegt"); return; } }
  const sc = simCfg(); let sections = [];
  if (mode === "sim") { list = blueprintSample(sc.full, state.exam === "pmp" ? 20 : 0); const cc = blueprintSample.caseCount;
    if (state.exam === "pmp") sections = [cc, cc + Math.round((list.length - cc) / 2)].filter(k => k > 0 && k < list.length); }
  if (mode === "simmini") list = blueprintSample(sc.mini);
  if (mode === "s1") list = shuffle((D.items || []).filter(i => i.set === "S1" && i.exam === "itil5"));
  if (mode === "s2") list = shuffle((D.items || []).filter(i => i.set === "S2" && i.exam === "itil5"));
  if (mode === "s3") list = shuffle((D.items || []).filter(i => i.set === "S3" && i.exam === "itil5"));
  if (mode === "s4") list = shuffle((D.items || []).filter(i => i.set === "S4" && i.exam === "itil5"));
  if (isMock(mode)) { list = shuffle((D.items || []).filter(i => i.exam === "pmp" && MOCK_MODES[mode].includes(i.set)));
    if (list.some(i => i.case)) { const cs = [...new Set(list.filter(i => i.case).map(i => i.case))]; list = cs.flatMap(c => list.filter(i => i.case === c).sort((a, b) => a.id.localeCompare(b.id))).concat(list.filter(i => !i.case)); }
    if (mode === "m1" || mode === "m2") sections = breakPoints(list); }
  if (mode === "sp1") list = (D.items || []).filter(i => i.set === "SP1" && i.exam === "itil5");
  if (mode === "sp2") list = (D.items || []).filter(i => i.set === "SP2" && i.exam === "itil5");
  if (mode === "new") list = openCands(items(), EVENTS);
  if (mode === "cards" || mode === "cardsmn") { cards = true; const st = srs(); list = shuffle(glossary().filter(g => (g.los || []).length && (mode === "cards" || hasHint(g)))).sort((a, b) => ((st[a.id] || {}).box || 0) - ((st[b.id] || {}).box || 0)).slice(0, 25); }
  if (mode.startsWith("trap:")) list = trapDrillList(mode.slice(5));
  if (mode === "gen") list = shuffle(items().filter(i => i.set === "GEN"));
  if (mode.startsWith("drill:")) list = shuffle((D.items || []).filter(i => i.exam === "pmp" && i.drill === mode.slice(6) && !rejected().has(i.id)));
  if (!list.length) { toast(mode === "lo" ? "Für dieses Lernziel gibt es noch keine Fragen – nutze die Glossarkarten" : "Keine Fragen verfügbar"); return; }
  const limit = (mode === "s1" || mode === "s2" || mode === "s3" || mode === "s4" || mode === "sp1" || mode === "sp2") ? 60 * 60 : mode === "sim" ? sc.fullMin * 60 : mode === "simmini" ? sc.miniMin * 60 : (isMock(mode) ? ((mode === "m1" || mode === "m2") ? sc.fullMin : sc.miniMin) * 60 : 0);
  run = { mode, list, i: 0, cards, answers: [], started: Date.now(), limit, sections, breaks: {}, pausedMs: 0 };
  if (sections.length) console.log("[XLRTE] Vollsimulation: Abschnittsgrenzen", sections, "Fallblock", blueprintSample.caseCount);
  $("#trainMenu").classList.add("hide"); $("#trainRun").classList.remove("hide"); renderRun();
  if (run.limit) { clearInterval(run.t); run.t = setInterval(simTick, 1000); simTick(); }
}
function runMinutes(r, now) { return Math.round((now - r.started - (r.pausedMs || 0)) / 60000); }
function pauseCredit(r, now) { return Math.min(now, r.pauseUntil) - r.pauseStart; }
function simRemaining(r, now) { const inPause = r.pauseUntil ? now - r.pauseStart : 0; return r.limit - Math.floor((now - r.started - r.pausedMs - inPause) / 1000); }
function simTick() {
  if (!run || !run.limit) return;
  const now = Date.now(), mmss = x => x > 0 ? Math.floor(x / 60) + ":" + String(x % 60).padStart(2, "0") : "0:00";
  if (run.pauseUntil) { const pe = $("#simClock"); if (pe) pe.textContent = mmss(simRemaining(run, now)); const pr = Math.ceil((run.pauseUntil - now) / 1000); const pc = $("#pauseClock"); if (pc) pc.textContent = mmss(pr); if (pr <= 0) endPause(); return; }
  const r = simRemaining(run, now); const el = $("#simClock"); if (el) el.textContent = mmss(r);
  const se = $("#shotClock"); if (se && run.qStart) { const rem = run.qBudget - Math.floor((now - run.qStart) / 1000); se.textContent = fmtShot(rem); const chip = $("#shotChip"); if (chip) chip.className = "chip shot " + shotState(rem, run.qBudget); }
  if (r <= 0) finishRun();
}
function stopRun() { if (run && run.t) clearInterval(run.t); run = null; $("#trainRun").classList.add("hide"); $("#trainMenu").classList.remove("hide"); renderTrainingMenu(); }
function renderRun() {
  if (!run) return; if (run.i >= run.list.length) return finishRun();
  if (run.sections && run.sections.includes(run.i) && !run.breaks[run.i]) return renderBreak();
  if (run.limit && run.qIdx !== run.i) { run.qIdx = run.i; run.qStart = Date.now(); const q0 = run.list[run.i]; run.qBudget = shotBudget(run.limit, run.list.length, !!q0.case && (run.i === 0 || run.list[run.i - 1].case !== q0.case)); }
  const it = run.list[run.i]; const head = `<div class="row" style="justify-content:space-between"><span class="label">${esc(modes().find(x => x[0] === run.mode)?.[1] || "Lernziel-Drill")} · ${run.i + 1} / ${run.list.length}</span><span class="row">${run.limit ? `<span class="chip">⏱ <b id="simClock"></b></span>` : ""}${run.limit && shotOn() ? `<span class="chip shot" id="shotChip" title="Zeit pro Frage (Pacing). Klick blendet die Shot Clock aus.">Frage <b id="shotClock"></b></span>` : ""}<button class="btn ghost sm" id="rStop">Beenden</button></span></div>`;
  if (run.cards) {
    $("#trainRun").innerHTML = `<div class="qbox">${head}<div class="flash" id="flash"><span class="label">Begriff · ${esc((it.los || []).join(", "))}</span><div class="term">${esc(it.term)}</div><div class="small muted" id="fHint">Definition laut aussprechen, dann aufdecken (Leertaste)</div><div class="small hide" id="fBack">${cardBackHTML(it)}</div></div>
      <div class="hide" id="fNote" style="margin-top:8px"><label class="tiny muted">Meine Eselsbrücke (wird gespeichert)</label><textarea id="mnText" style="min-height:48px;margin-top:4px" placeholder="z. B. ein eigener Merksatz, ein Bild oder ein Beispiel aus deinem Alltag">${esc(settings()["mn." + it.id] || "")}</textarea><div class="row" style="margin-top:4px"><button class="btn ghost sm" id="mnSave">Speichern</button></div></div>
      <div class="row hide" id="fGrade" style="margin-top:12px"><button class="btn ghost" data-g="0">Nicht gewusst <kbd>1</kbd></button><button class="btn ghost" data-g="1">Lückenhaft <kbd>2</kbd></button><button class="btn" data-g="2">Gewusst <kbd>3</kbd></button><button class="btn" data-g="3">Sofort <kbd>4</kbd></button></div></div>`;
    $("#flash").onclick = reveal; $$("#fGrade [data-g]").forEach(b => b.onclick = () => gradeCard(+b.dataset.g));
  } else {
    if (it.type === "num") { run.sel = null; run.done = false; $("#trainRun").innerHTML = numHTML(it, head); wireNum(it); $("#rStop").onclick = stopRun; wireShot(); return; }
    const multi = it.type === "multi"; const order = shuffle(it.options.map((_, k) => k)); run.order = order; run.sel = multi ? [] : null;
    const cand = it.status === "candidate"; const cs = it.case ? (D.cases || []).find(c => c.id === it.case) : null;
    run.qf = run.qf || {};
    if (cs && !run.qf[cs.id] && qfirstOn(run.mode)) {
      const qs = run.list.filter(x => x.case === cs.id);
      $("#trainRun").innerHTML = `<div class="qbox">${head}${casePreviewHTML(cs, qs)}
        <div class="row" style="margin-top:12px"><button class="btn" id="qfGo">Fall lesen <kbd>Enter</kbd></button>${run.mode === "fall" ? "" : `<label class="row small" style="gap:6px;align-items:center"><input type="checkbox" id="qfSwitch" checked> „Fragen zuerst“ bei Fällen beibehalten</label>`}</div></div>`;
      $("#qfGo").onclick = () => { run.qf[cs.id] = true; renderRun(); }; $("#qfGo").focus();
      const sw = $("#qfSwitch"); if (sw) sw.onchange = () => addEvent("setting", { ref: "ui.qfirst", value: sw.checked });
      $("#rStop").onclick = () => (isSim(run.mode) && run.answers.length ? finishRun() : stopRun());
      wireShot();
      return;
    }
    $("#trainRun").innerHTML = `<div class="qbox">${head}${isSim(run.mode) ? "" : `<div class="small muted" style="margin-top:6px">${esc(it.lo)} · ${esc(loById(it.lo).text)} ${it.bl ? "· BL" + it.bl : ""} ${cand ? "<span class='pill acc'>neu · ungeprüft</span>" : ""}</div>`}
      ${cs ? `<details class="casebox" open><summary>Fall · ${esc(cs.title)}</summary><div class="small" style="margin-top:6px">${esc(cs.text)}</div>${cs.table ? `<table class="small" style="margin-top:8px">${cs.table.map((row, ri) => `<tr>${row.map(c => ri ? `<td>${esc(c)}</td>` : `<th>${esc(c)}</th>`).join("")}</tr>`).join("")}</table>` : ""}</details>` : ""}
      <div class="qstem">${esc(it.q)}</div>${figHTML(it)}${multi ? `<div class="small muted">Mehrfachauswahl: genau ${it.answer.length} Optionen markieren</div>` : ""}${it.stmts ? `<ol class="stmts">${it.stmts.map(s => `<li>${esc(s)}</li>`).join("")}</ol>` : ""}
      <div id="opts">${order.map((o, k) => `<button class="opt" data-o="${o}"><span class="k">${multi ? "☐ " : ""}${"ABCDEF"[k]}</span>${esc(it.options[o])}</button>`).join("")}</div>
      ${run.mode === "vorab" ? `<div class="row" id="conf" style="margin-top:10px"><span class="small muted">Ohne Vorwissen: bester Versuch, Raten ist erlaubt.</span><button class="btn" data-c="vorab" disabled>Antwort prüfen <kbd>Enter</kbd></button></div>` : `<div class="row" id="conf" style="margin-top:10px"><span class="small muted">Antwort abgeben:</span><button class="btn" data-c="sure" disabled>Sicher <kbd>Enter</kbd></button><button class="btn ghost" data-c="unsure" disabled>Unsicher</button><button class="btn ghost" data-c="guess" disabled>Geraten</button></div>`}
      <div id="fb"></div></div>`;
    $$("#opts .opt").forEach(b => b.onclick = () => { if (run.done) return; const o = +b.dataset.o;
      if (multi) { const k = run.sel.indexOf(o); if (k >= 0) run.sel.splice(k, 1); else if (run.sel.length < it.answer.length) run.sel.push(o); else toast(`Genau ${it.answer.length} Optionen – erst eine Auswahl aufheben`); b.classList.toggle("sel", run.sel.includes(o)); $$("#conf button").forEach(x => x.disabled = run.sel.length !== it.answer.length); return; }
      $$("#opts .opt").forEach(x => x.classList.remove("sel")); b.classList.add("sel"); run.sel = o; $$("#conf button").forEach(x => x.disabled = false); });
    $$("#conf button").forEach(b => b.onclick = () => answer(b.dataset.c));
    run.done = false;
  }
  $("#rStop").onclick = () => (isSim(run.mode) && run.answers.length ? finishRun() : stopRun());
  wireShot();
}
function renderBreak() {
  const k = run.sections.indexOf(run.i) + 1;
  $("#trainRun").innerHTML = `<div class="qbox"><div class="label">Abschnitt ${k} abgeschlossen · ${run.i} / ${run.list.length}</div><h3 style="margin:8px 0">Optionale Pause (10 Min)</h3>
    <div class="small muted">Wie in der echten Prüfung: Nach der Pause kannst du nicht zu früheren Fragen zurück. Die Pausenzeit zählt nicht zur Prüfungszeit.</div>
    <div class="row" style="margin-top:8px"><span class="chip">Prüfungszeit ⏱ <b id="simClock"></b></span><button class="btn ghost sm" id="rStop">Simulation beenden</button></div>
    <div class="row" style="margin-top:12px">${run.pauseUntil ? `<span class="chip">Pause ⏱ <b id="pauseClock"></b></span><button class="btn" id="bEnd">Pause beenden</button>` : `<button class="btn" id="bPause">Pause starten</button><button class="btn ghost" id="bSkip">Weiter ohne Pause</button>`}</div></div>`;
  if ($("#bPause")) $("#bPause").onclick = () => { run.pauseStart = Date.now(); run.pauseUntil = Date.now() + 10 * 60 * 1000; renderBreak(); };
  if ($("#bSkip")) $("#bSkip").onclick = () => { run.breaks[run.i] = true; renderRun(); };
  if ($("#bEnd")) $("#bEnd").onclick = endPause;
  $("#rStop").onclick = () => (run.answers.length ? finishRun() : stopRun()); simTick();
}
function endPause() { if (!run || !run.pauseUntil) return; run.pausedMs += pauseCredit(run, Date.now()); run.pauseUntil = null; run.breaks[run.i] = true; renderRun(); }
function reveal() { if (!run || !run.cards) return; $("#fBack").classList.remove("hide"); $("#fHint").classList.add("hide"); $("#fGrade").classList.remove("hide"); const fn = $("#fNote"); if (fn) { fn.classList.remove("hide"); $("#mnSave").onclick = () => { const it = run.list[run.i]; addEvent("setting", { ref: "mn." + it.id, value: $("#mnText").value.trim() }); toast("Eselsbrücke gespeichert"); }; } }
function gradeCard(g) { const it = run.list[run.i]; addEvent("card", { ref: it.id, value: g, exam: state.exam }); run.answers.push({ it, ok: g >= 2 }); run.i++; renderRun(); }
function answer(conf) {
  const it = run.list[run.i]; const multi = it.type === "multi";
  if (run.sel === null || run.done || (multi && run.sel.length !== it.answer.length)) return; run.done = true;
  const right = multi ? it.answer : [it.answer]; const picked = multi ? run.sel.slice().sort((a, b) => a - b) : [run.sel];
  const ok = picked.length === right.length && picked.every((v, k) => v === right.slice().sort((a, b) => a - b)[k]);
  addEvent("attempt", { ref: it.id, value: ok ? 1 : 0, exam: it.exam, meta: Object.assign({ conf, mode: run.mode }, multi ? { picked } : { pick: run.sel }, run.limit && run.qStart ? { secs: Math.round((Date.now() - run.qStart) / 1000) } : {}) });
  const secs =run.limit && run.qStart ? Math.round((Date.now() - run.qStart) / 1000) : undefined;
  run.answers.push({ it, ok, conf, sel: run.sel, secs, budget: secs === undefined ? undefined : run.qBudget });
  if (isSim(run.mode)) { run.i++; return renderRun(); }
  $$("#opts .opt").forEach(b => { const o = +b.dataset.o; if (right.includes(o)) b.classList.add("ok"); else if (picked.includes(o)) b.classList.add("no"); });
  $$("#conf button").forEach(x => x.disabled = true);
  const l = loById(it.lo);
  $("#fb").innerHTML = `<div class="feedback ${ok ? "ok" : "no"}"><b>${run.mode === "vorab" ? (ok ? "Richtig – stark ohne Vorwissen" : "Noch nicht – genau dafür ist der Vorab-Test da") : ok ? (conf === "guess" ? "Richtig – aber geraten (zählt halb)" : "Richtig") : "Incident: falsch"}</b><br>${esc(whyMapped(it.why, run.order))}<div class="tiny muted" style="margin-top:6px">Lernziel ${esc(it.lo)}${it.book ? " · PMBOK 8 " + esc(it.book) : ""} · ${l.book ? "Buch §" + esc(l.book) : esc(ritaRef(l) || l.focus || "")}</div></div>
    <div class="row" style="margin-top:10px"><button class="btn" id="next">Weiter <kbd>→</kbd></button>${it.status === "candidate" ? `<button class="btn ghost sm" data-rv="1">Frage ist gut</button><button class="btn ghost sm" data-rv="0">Frage verwerfen</button>` : ""}</div>`;
  if (!ok && trapsOn() && state.exam === "pmp" && run.mode !== "vorab") { const tg = ((D.traps || {}).items || {})[it.id] || [];
    if (tg.length) { const lure = ((D.traps || {}).lures || {})[it.id] || {}; const hit = !multi && lure[run.sel] ? " Du hast die verlockende Option dieser Falle gewählt." : "";
      $("#fb").insertAdjacentHTML("beforeend", `<div class="tiny" style="margin-top:6px"><b>Falle:</b> ${tg.map(t => esc(trapName(t)) + " – " + esc(trapRule(t))).join(" · ")}${hit}</div>`); } }
  $("#next").onclick = () => { run.i++; renderRun(); };
  if (!ok && conf === "sure" && run.mode !== "vorab") {   /* hypercorrection: a confident error is the best learning moment — name the confusion */
    $("#next").disabled = true;
    $("#fb").insertAdjacentHTML("beforeend", `<div class="copybox small" style="margin-top:10px"><b>Warum lag ich falsch?</b> Was habe ich verwechselt, und woran erkenne ich es künftig? (1 Satz)
      <textarea id="refl" style="min-height:56px;margin-top:6px" placeholder="z. B. Ich habe Output und Outcome verwechselt – Outcome ist das Resultat für den Stakeholder."></textarea>
      <div class="row" style="margin-top:6px"><button class="btn sm" id="reflSave">Merkhilfe speichern</button><span class="tiny muted">wird als Known Error zum Lernziel ${esc(it.lo)} abgelegt</span></div></div>`);
    $("#reflSave").onclick = () => { const t = $("#refl").value.trim(); if (t.length < 8) return toast("Bitte kurz formulieren, was du verwechselt hast");
      addEvent("workaround", { ref: it.lo, exam: it.exam, meta: { text: t, item: it.id, source: "hyper" } }); toast("Merkhilfe gespeichert (+15 XP)"); $("#reflSave").disabled = true; $("#next").disabled = false; };
  }
  $$("[data-rv]").forEach(b => b.onclick = () => { addEvent("review", { ref: it.id, value: +b.dataset.rv, exam: it.exam }); toast(+b.dataset.rv ? "Übernommen" : "Verworfen"); b.parentNode.querySelectorAll("[data-rv]").forEach(x => x.disabled = true); });
}
function finishRun() {
  if (!run) return; if (run.t) clearInterval(run.t);
  if (isSim(run.mode) && !run.answers.length) { toast("Keine Antwort gegeben – Prüfung nicht gewertet"); return stopRun(); }
  const a = run.answers, n = a.length, ok = a.filter(x => x.ok).length; if (run.pauseUntil) run.pausedMs += pauseCredit(run, Date.now()); const mins = runMinutes(run, Date.now());
  if (mins >= 5) addEvent("focus", { minutes: mins, ref: "training:" + run.mode, meta: { text: `${modes().find(x => x[0] === run.mode)?.[1] || "Drill"}: ${ok}/${n} richtig` } });
  let byCat = "";
  if (!run.cards) { const cats = {}; a.forEach(x => { const c = loById(x.it.lo).cat; cats[c] = cats[c] || [0, 0]; cats[c][1]++; if (x.ok) cats[c][0]++; }); byCat = `<table style="margin-top:10px"><tr><th>Kategorie</th><th class="num">Richtig</th></tr>${Object.keys(cats).sort().map(c => `<tr><td>${esc(c)} · ${esc((bank().categories.find(k => k.id === c) || {}).name)}</td><td class="num">${cats[c][0]}/${cats[c][1]}</td></tr>`).join("")}</table>`; }
  let byTrap = "";
  if (!run.cards && state.exam === "pmp") { const tg = (D.traps || {}).items || {}, tr = {};
    a.forEach(x => (tg[x.it.id] || []).forEach(t => { tr[t] = tr[t] || [0, 0]; tr[t][1]++; if (x.ok) tr[t][0]++; }));
    if (Object.keys(tr).length) byTrap = `<table style="margin-top:10px"><tr><th>Fallen dieser Runde</th><th class="num">Richtig</th></tr>${Object.keys(tr).sort((p, q) => tr[p][0] / tr[p][1] - tr[q][0] / tr[q][1]).map(t => `<tr><td>${esc(trapName(t))}</td><td class="num">${tr[t][0]}/${tr[t][1]}</td></tr>`).join("")}</table>`; }
  if (isSim(run.mode)) { const of = run.list.length; const ref = run.mode === "simmini" ? "XLRTE-SIM-MINI" : run.mode === "s1" ? "XLRTE-S1" : run.mode === "s2" ? "XLRTE-S2" : run.mode === "s3" ? "XLRTE-S3" : run.mode === "s4" ? "XLRTE-S4" : run.mode === "sp1" ? "SP1" : run.mode === "sp2" ? "SP2" : isMock(run.mode) ? "XLRTE-" + run.mode.toUpperCase() : "XLRTE-SIM"; addEvent("exam", { ref, value: ok, meta: { of, answered: n, pass: ok / of >= (examCfg().pass_pct || 65) / 100, mins } }); }
  { const pz = paceSummary(a); if (pz && isSim(run.mode)) addEvent("note", { ref: "pace", value: pz.avg, meta: { mode: run.mode, bud: pz.bud, over: pz.over, n: pz.n } }); }
  const wrong = a.filter(x => !x.ok && !run.cards);
  $("#trainRun").innerHTML = `<div class="qbox"><div class="label">Ergebnis</div><div class="hero-num" style="margin:8px 0">${ok} <small>/ ${n} · ${n ? pct(ok / n) : "–"} · ${mins} Min</small></div>${byCat}${byTrap}${paceHTML(paceSummary(a))}${stemHTML(run.list)}
    ${run.mode === "vorab" ? `<div class="feedback ok small" style="margin-top:10px">Vorab-Test: zählt nicht für Prognose, Wiederholung und Fehler-Management. Achte im Kurs besonders auf die Punkte unten.</div>` : ""}${wrong.length ? `<h3 style="margin-top:16px">${run.mode === "vorab" ? "Darauf achtest du heute im Kurs" : "Incidents dieser Runde"}</h3>` + wrong.map(x => `<div class="feedback no small"><b>${esc(x.it.q)}</b><br>Richtig: ${esc(rightText(x.it))}<br><span class="muted">${esc(x.it.why)}</span></div>`).join("") : ""}
    <div class="row" style="margin-top:14px"><button class="btn" id="again">Zurück zum Training</button>${run.mode === "vorab" ? "" : `<button class="btn ghost" id="toBoard">Fehler-Management öffnen</button>`}</div></div>`;
  run = null; $("#again").onclick = stopRun; if ($("#shotBack")) $("#shotBack").onclick = () => { addEvent("setting", { ref: "ui.shotclock", value: true }); $("#shotBack").disabled = true; }; if ($("#toBoard")) $("#toBoard").onclick = () => { stopRun(); go("fehler"); };
}
document.addEventListener("keydown", e => {
  if (!run || state.view !== "training" || /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
  if (run.cards) { if (e.key === " ") { e.preventDefault(); reveal(); } if (["1", "2", "3", "4"].includes(e.key) && !$("#fGrade").classList.contains("hide")) gradeCard(+e.key - 1); return; }
  if (!$("#opts")) return;
  if (["1", "2", "3", "4", "5", "a", "b", "c", "d", "e"].includes(e.key.toLowerCase()) && !run.done) { const k = "12345".includes(e.key) ? +e.key - 1 : "abcde".indexOf(e.key.toLowerCase()); const b = $$("#opts .opt")[k]; if (b) b.click(); }
  if (e.key === "Enter" && !run.done && run.sel !== null && !(Array.isArray(run.sel) && run.sel.length !== run.list[run.i].answer.length)) answer("sure");
  else if ((e.key === "ArrowRight" || e.key === "Enter") && run.done && $("#next")) $("#next").click();
});

/* ---------------------------------------------------------------- fehler-management */
function renderBoard() {
  const b = incidentBoard(); const lo = id => loById(id);
  const col = (t, arr, fn) => `<div class="col"><h4><span>${t}</span><span class="muted">${t.startsWith("Incidents") ? b.inc.length : arr.length}</span></h4>${arr.map(fn).join("") || "<div class='tiny muted' style='padding:4px'>leer</div>"}</div>`;
  $("#board").innerHTML =
    col("Incidents (14 Tage)", b.inc.slice(0, 8).concat(b.inc.length > 8 ? [{ more: b.inc.length - 8 }] : []), x => x.more ? `<div class="tiny muted" style="padding:4px">+ ${x.more} weitere – im Schwachstellen-Drill enthalten</div>` : `<div class="tkt"><div class="t">${esc(x.lo)} ${esc(lo(x.lo).text)}</div><div class="tiny muted">1× falsch · ${esc(x.e.date)}</div><button class="btn ghost sm" style="margin-top:6px" data-go="lo" data-lo="${esc(x.lo)}">Erneut testen</button></div>`)
    + col("Problems", b.prob, x => `<div class="tkt p"><div class="t">${esc(x.lo)} ${esc(lo(x.lo).text)}</div><div class="tiny muted">${x.n}× falsch · Ursache analysieren: Buch §${esc(lo(x.lo).book || "–")}</div><textarea placeholder="Workaround / Merkhilfe: Was verwechsle ich, und woran erkenne ich es künftig?" data-wk="${esc(x.lo)}" style="min-height:70px;margin-top:6px"></textarea><button class="btn sm" style="margin-top:6px" data-wks="${esc(x.lo)}">Als Known Error erfassen</button></div>`)
    + col("Known Errors", b.ke, x => `<div class="tkt"><div class="t">${esc(x.lo)} ${esc(lo(x.lo).text)}</div><div class="small" style="margin:4px 0">${esc((x.wk.meta || {}).text)}</div><button class="btn ghost sm" data-go="lo" data-lo="${esc(x.lo)}">Lösung prüfen (3 richtige in Folge)</button></div>`)
    + col("Gelöst", b.solved, x => `<div class="tkt"><div class="t">✓ ${esc(x.lo)} ${esc(lo(x.lo).text)}</div></div>`);
  $$("[data-wks]").forEach(btn => btn.onclick = () => { const id = btn.dataset.wks; const t = $(`[data-wk="${id}"]`).value.trim(); if (t.length < 8) return toast("Bitte eine kurze Merkhilfe formulieren"); addEvent("workaround", { ref: id, meta: { text: t } }); toast("Known Error erfasst (+15 XP)"); });
}

/* ---------------------------------------------------------------- EVM */
function workdays(a, b) { let n = 0; const d = new Date(a + "T12:00"), e = new Date(b + "T12:00"); while (d <= e) { const w = d.getDay(); if (w && w !== 6) n++; d.setDate(d.getDate() + 1); } return n; }
function renderEVM() {
  const ex = examCfg(); const m = model(); const solid = (C.mastery || {}).solid || .8;
  const start = ex.plan_start, end = ex.target_date, bac = +ex.plan_hours || 40, tot = Math.max(1, workdays(start, end));
  const base = (C.mastery || {}).prior_a / (((C.mastery || {}).prior_a || .5) + ((C.mastery || {}).prior_b || 1.5)) || .25;
  const evFrac = Object.keys(m.mm).reduce((s, k) => s + (m.lw[k] || 0) * Math.max(0, Math.min(1, (m.mm[k].m - base) / (solid - base))), 0);
  const days = []; const d = new Date(start + "T12:00"); const last = TODAY < end ? TODAY : end;
  let acCum = 0; const acBy = {}; EVENTS.filter(e => e.exam === state.exam && (e.kind === "focus" || e.kind === "activity")).forEach(e => acBy[e.date] = (acBy[e.date] || 0) + (+e.minutes || 0) / 60);
  const endD = new Date(end + "T12:00");
  while (d <= endD) { const iso = localISO(d); acCum += acBy[iso] || 0; days.push({ iso, pv: bac * workdays(start, iso) / tot, ac: iso <= last ? acCum : null }); d.setDate(d.getDate() + 1); }
  const pv = TODAY < start ? 0 : bac * workdays(start, last) / tot, ev = bac * evFrac, ac = days.filter(x => x.ac !== null).slice(-1)[0]?.ac || 0;
  const spi = pv ? ev / pv : null, cpi = ac ? ev / ac : null;
  const tile = (l, v, f, s) => `<div class="card"><div class="label">${l}</div><div class="hero-num" style="font-size:34px;margin:6px 0">${v}</div><div class="tiny muted">${f}</div>${s ? `<div class="small ${s[1]}">${s[0]}</div>` : ""}</div>`;
  const stat = (x, good, txt) => x === null ? ["–", "muted"] : x >= 1 ? [good, "status-ok"] : x >= .9 ? ["leicht " + txt, "status-warn"] : [txt, "status-bad"];
  $("#evmTiles").innerHTML = tile("SPI", spi ? spi.toFixed(2) : "–", "EV / PV", stat(spi, "im Plan oder voraus", "hinter Plan")) + tile("CPI", cpi ? cpi.toFixed(2) : "–", "EV / AC", stat(cpi, "effizient", "Mehraufwand")) + tile("EAC", cpi ? fmt1(bac / cpi) + " h" : "–", "BAC / CPI – Prognose Gesamtaufwand") + tile("EV / BAC", pct(evFrac), `${fmt1(ev)} h von ${bac} h verdient`);
  // chart: PV line (full), AC line (to today), EV point today
  const W = 900, H = 280, L = 44, R = 70, T = 16, Bm = 30; const maxY = Math.max(bac, ac, ev) * 1.1; const n = days.length - 1 || 1;
  const X = i => L + (W - L - R) * i / n, Y = v => T + (H - T - Bm) * (1 - v / maxY);
  const pathOf = key => days.map((p, i) => p[key] === null ? null : `${X(i).toFixed(1)},${Y(p[key]).toFixed(1)}`).filter(Boolean).map((s, i) => (i ? "L" : "M") + s).join("");
  const ti = days.findIndex(p => p.iso === last);
  let g = ""; for (let k = 0; k <= 4; k++) { const v = maxY * k / 4; g += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)" stroke-width="1"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${Math.round(v)} h</text>`; }
  const xt = days.map((p, i) => i % Math.ceil(days.length / 8) === 0 ? `<text x="${X(i)}" y="${H - 10}" text-anchor="middle">${p.iso.slice(8, 10)}.${p.iso.slice(5, 7)}.</text>` : "").join("");
  const acLast = days[ti] ? days[ti] : days[0];
  $("#evmChart").innerHTML = g + xt + `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--neutral)"/>
    <path d="${pathOf("pv")}" fill="none" stroke="var(--s2)" stroke-width="2"/><path d="${pathOf("ac")}" fill="none" stroke="var(--s3)" stroke-width="2"/>
    ${ti >= 0 ? `<circle cx="${X(ti)}" cy="${Y(ev)}" r="6" fill="var(--s1)" stroke="var(--paper)" stroke-width="2"/><text x="${X(ti) + 10}" y="${Y(ev) - 8}" style="fill:var(--ink)">EV ${fmt1(ev)} h</text>` : ""}
    <text x="${W - R + 6}" y="${Y(bac) + 4}" style="fill:var(--ink)">PV · BAC ${bac} h</text>${ti >= 0 && acLast.ac !== null ? `<text x="${X(ti) + 10}" y="${Y(acLast.ac) + 14}" style="fill:var(--ink)">AC ${fmt1(acLast.ac)} h</text>` : ""}
    <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - Bm}" fill="transparent" id="evmHit"/>`;
  const hit = $("#evmHit"), tip = $("#tip");
  hit.onmousemove = e => { const r = $("#evmChart").getBoundingClientRect(); const x = (e.clientX - r.left) / r.width * W; const i = Math.max(0, Math.min(n, Math.round((x - L) / (W - L - R) * n))); const p = days[i]; tip.style.display = "block"; tip.style.left = e.clientX + 12 + "px"; tip.style.top = e.clientY + 12 + "px"; tip.textContent = `${new Date(p.iso + "T12:00").toLocaleDateString("de-DE")} · PV ${fmt1(p.pv)} h${p.ac !== null ? " · AC " + fmt1(p.ac) + " h" : ""}`; };
  hit.onmouseleave = () => tip.style.display = "none";
  $("#evmTable").innerHTML = `<table style="margin-top:10px"><tr><th>Größe</th><th class="num">Wert</th><th>Formel (PMI)</th></tr><tr><td>BAC</td><td class="num">${bac} h</td><td>Budget at Completion = geplante Lernstunden</td></tr><tr><td>PV</td><td class="num">${fmt1(pv)} h</td><td>Planwert bis heute (linear über Arbeitstage)</td></tr><tr><td>EV</td><td class="num">${fmt1(ev)} h</td><td>BAC × Σ Gewicht × Fortschritt von Ratewert (25 %) bis „gefestigt“ (${solid * 100} %)</td></tr><tr><td>AC</td><td class="num">${fmt1(ac)} h</td><td>geloggte Lern- und Fokuszeit</td></tr><tr><td>SV / CV</td><td class="num">${fmt1(ev - pv)} / ${ac ? fmt1(ev - ac) : "–"} h</td><td>EV − PV / EV − AC</td></tr></table>`;
  $("#phaseList").innerHTML = (C.phases || []).map(p => `<div class="phase ${p.from <= TODAY && TODAY <= p.to ? "now" : ""}"><span class="d">${new Date(p.from + "T12:00").toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })}–${new Date(p.to + "T12:00").toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })}</span><span>${esc(p.name)} <span class="muted">· ${esc(p.mode)}</span></span></div>`).join("");
}

/* ---------------------------------------------------------------- journal & attendance */
function currentExamForAttendance() { const ph = currentPhase(); return examList().includes(ph.exam) ? ph.exam : state.exam; }
const ACT = { video: "Ninja-Training Videomodul", book: "Lektüre offizielles Buch", classroom: "Teilnahme Live-Training", handout: "Durcharbeiten Handout/Glossar", notebook: "Quellengestützte Wiederholung (Gemini Notebook)", mentoring: "Mentoring-/Beratungsgespräch", mock: "Musterprüfung", other: "" };
function logoutText(date = TODAY) {
  const st = dayStats(date); const ph = currentPhase();
  const parts = st.acts.map(a => { const t = (a.meta || {}).text || ""; const lead = ACT[a.ref] || ""; return (lead && t ? lead + ": " + t : lead || t) + (a.minutes ? ` (${a.minutes} Min)` : ""); });
  const trainings = st.es.filter(e => e.kind === "focus" && (e.ref || "").startsWith("training")).map(e => (e.meta || {}).text).filter(Boolean);
  const itemsById = {}; (D.items || []).forEach(i => itemsById[i.id] = i);
  const cats = {}; st.att_events.forEach(e => { const it = itemsById[e.ref]; if (it) { const l = loById(it.lo, it.exam); const n = (bank(it.exam).categories.find(c => c.id === l.cat) || {}).name; if (n) cats[n] = 1; } });
  const wk = st.es.filter(e => e.kind === "workaround").length;
  const sim = st.es.filter(e => e.kind === "exam");
  let s = parts.join("; ");
  if (st.att) s += (s ? ". " : "") + `Bearbeitung von ${st.att} Übungsfragen (${Math.round(st.ok / st.att * 100)} % korrekt)` + (Object.keys(cats).length ? ` zu: ${Object.keys(cats).slice(0, 4).join(", ")}` : "");
  const cardsBy = x => st.es.filter(e => e.kind === "card" && (e.exam || "itil5") === x).length;
  const cardTxt = [cardsBy("itil5") ? `${cardsBy("itil5")} Lernkarten zu offiziellen ITIL-Definitionen` : "", cardsBy("pmp") ? `${cardsBy("pmp")} PMP-Begriffskarten (Formeln, Vertragsarten, agile Artefakte)` : "",
    ...examList().filter(x => x !== "itil5" && x !== "pmp" && cardsBy(x)).map(x => `${cardsBy(x)} Lernkarten (${examCfg(x).name || x})`)].filter(Boolean);
  if (cardTxt.length) s += (s ? "; " : "") + cardTxt.join(" und ") + " wiederholt";
  const SIMNAME = { "XLRTE-SIM": "Prüfungssimulation", "XLRTE-SIM-MINI": "Mini-Prüfungssimulation", "XLRTE-S1": "Schattenprüfung S1", "XLRTE-S2": "Schattenprüfung S2", "XLRTE-S3": "Schattenprüfung S3", "XLRTE-S4": "Schattenprüfung S4 (SP-Form)", "XLRTE-M1A": "PMP Mock 1 · Teil A", "XLRTE-M1B": "PMP Mock 1 · Teil B", "XLRTE-M1C": "PMP Mock 1 · Teil C", "XLRTE-M1": "PMP Vollmock 1 (180)", "XLRTE-SZ1": "Szenario-Set 1", "XLRTE-SZ2": "Szenario-Set 2", "XLRTE-M2B": "PMP Mock 2 · Teil B", "XLRTE-M2C": "PMP Mock 2 · Teil C", "XLRTE-M2": "PMP Vollmock 2 (180)", "XLRTE-MBP": "PMI Übungsfragen People", "XLRTE-MBR": "PMI Übungsfragen Process", "XLRTE-MBB": "PMI Übungsfragen Business Environment", "XLRTE-M2A": "PMP Fallen-Mock 2", "XLRTE-M3A": "PMP Mock 3 · Prüfungskaliber", "SP1": "Offizielle Musterprüfung SP1", "SP2": "Offizielle Musterprüfung SP2" };
  if (sim.length) s += "; " + sim.map(e => `${SIMNAME[e.ref] || e.ref}: ${e.value}/${(e.meta || {}).of || 40} Punkte`).join(", ");
  if (wk) s += `; Fehleranalyse und ${wk} Merkhilfe(n) zu Wissenslücken erstellt`;
  if (!s) s = "";
  return s ? s.replace(/;\s*;/g, ";") + "." : "";
}
/* Daily recap: today benchmarked against the learner's own learning period (all earlier days with practice) and the last 7. */
function recapStats(today = TODAY) {
  const days = [...new Set(EVENTS.filter(e => e.date < today && ["attempt", "card", "focus", "activity"].includes(e.kind)).map(e => e.date))].sort();
  const row = d => { const s = dayStats(d); return { ret: s.ret, acc: s.att ? s.ok / s.att : null, focus: s.focus, wrong: s.att - s.ok }; };
  const avg = (rs, k) => { const v = rs.map(r => r[k]).filter(x => x !== null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  const all = days.map(row), last7 = days.slice(-7).map(row), t = row(today);
  const top = k => { const v = all.map(r => r[k]).filter(x => x !== null); return v.length ? Math.max(...v) : null; };
  const metric = (k, label, f) => ({ label, today: t[k], avg: avg(all, k), last7: avg(last7, k), best: top(k), f });
  return { n: days.length, from: days[0] || today, rows: [metric("ret", "Abrufe (Fragen + Karten)", v => Math.round(v)), metric("acc", "Trefferquote", v => pct(v)), metric("focus", "Lern- und Fokuszeit (Min)", v => Math.round(v)), metric("wrong", "Fehler = Lernchancen", v => Math.round(v))] };
}
function recapText(r) {
  const fmt = (m, v) => v === null || v === undefined ? "–" : m.f(v);
  const head = `Tages-Recap ${deDate(TODAY)} · Lernzeitraum seit ${deDate(r.from)} (${r.n} Lerntage)`;
  const lines = r.rows.map(m => `- ${m.label}: heute ${fmt(m, m.today)} · Ø Zeitraum ${fmt(m, m.avg)} · Ø 7 Tage ${fmt(m, m.last7)}`);
  const top = model().weak[0];
  return [head, ...lines, top ? `- Größte Lücke: ${top.lo.id} ${top.lo.text}` : "", logoutText() ? "- Heute: " + logoutText() : ""].filter(Boolean).join("\n");
}
function renderRecap() {
  const el = $("#recapCard"); if (!el) return;
  const r = recapStats(), done = EVENTS.find(e => e.date === TODAY && e.kind === "recap");
  const fmt = (m, v) => v === null || v === undefined ? "–" : m.f(v);
  const cmp = m => m.avg === null || m.today === null ? "" : m.today >= m.avg ? "status-ok" : "status-warn";
  el.innerHTML = `<div class="row" style="justify-content:space-between"><div><div class="label">Tages-Recap</div><h3>Dein Tag gegen deinen Lernzeitraum</h3></div><span class="pill ${done ? "solid" : ""}">${done ? "gespeichert " + done.ts.slice(11, 16) : "offen"}</span></div>
    <table class="small" style="margin-top:8px"><tr><th>Messgröße</th><th class="num">Heute</th><th class="num">Ø Zeitraum</th><th class="num">Ø 7 Tage</th><th class="num">Bestwert</th></tr>${r.rows.map(m => `<tr><td>${m.label}</td><td class="num ${cmp(m)}">${fmt(m, m.today)}</td><td class="num">${fmt(m, m.avg)}</td><td class="num">${fmt(m, m.last7)}</td><td class="num">${fmt(m, m.best)}</td></tr>`).join("")}</table>
    <textarea id="recapText" style="min-height:110px;margin-top:10px">${esc(recapText(r))}</textarea>
    <div class="row" style="margin-top:8px"><span class="small muted">Lernzeitraum seit ${deDate(r.from)} · ${r.n} Lerntage. Der Recap geht ins Journal und ins Lernprofil für deinen KI-Tutor.</span><div class="spacer"></div><button class="btn sm ghost" id="recapCopy">Kopieren</button><button class="btn sm" id="recapSave">${done ? "Neu speichern" : "Recap speichern"}</button></div>`;
  $("#recapCopy").onclick = () => copy($("#recapText").value);
  $("#recapSave").onclick = () => { const m = Object.fromEntries(r.rows.map(x => [x.label, { today: x.today, avg: x.avg, last7: x.last7 }])); addEvent("recap", { ref: "day", value: r.rows[0].today, exam: state.exam, meta: { text: $("#recapText").value, metrics: m, days: r.n } }); toast("Recap gespeichert"); renderJournal(); };
}
function renderJournal() {
  const ph = currentPhase();
  renderRecap();
  if ($("#attCard")) $("#attCard").style.display = COURSE ? "" : "none";
  if (!COURSE) { Object.assign(ACT, { video: "Video / Online-Kurs", book: "Buch / Lektüre", classroom: "Kurs / Live-Training", handout: "Skript / Glossar", notebook: "KI-Tutor / Notebook", mentoring: "Lerngruppe / Mentoring", mock: "Übungsprüfung" }); $$("#actType option").forEach(o => { if (ACT[o.value]) o.textContent = ACT[o.value]; }); }
  $("#attTitle").textContent = deDate(TODAY) + " · " + ph.name;
  $("#teamsLink").href = C.teams_url || "https://teams.microsoft.com";
  const login = EVENTS.find(e => e.date === TODAY && e.kind === "attendance" && e.ref === "login"), logout = EVENTS.find(e => e.date === TODAY && e.kind === "attendance" && e.ref === "logout");
  const abs = EVENTS.filter(e => e.date === TODAY && e.kind === "attendance" && e.ref === "absence");
  $("#btnLogin").textContent = login ? "Login " + login.ts.slice(11, 16) + " ✓" : "Login erfassen"; $("#btnLogin").disabled = !!login;
  $("#attState").innerHTML = `Kernlernzeit ${C.core_hours?.login || "09:00"}–${C.core_hours?.logout_to || "17:00"} · ${logout ? "Logout " + logout.ts.slice(11, 16) + " ✓" : "Logout offen"}${abs.length ? " · Fehlzeit: " + abs.map(a => esc(a.meta.type + " " + a.meta.from + "–" + a.meta.to)).join(", ") : ""}`;
  $("#attCourse").innerHTML = `Kurs im Formular: <b>${esc(ph.attendance_course || "")}</b>`;
  if (!$("#logoutText").dataset.touched) $("#logoutText").value = logoutText();
  const st = dayStats(TODAY);
  $("#todayLog").innerHTML = `<table><tr><th>Zeit</th><th>Eintrag</th><th class="num">Min</th></tr>${st.es.filter(e => ["activity", "focus", "attendance", "exam", "workaround"].includes(e.kind)).map(e => `<tr><td>${esc((e.ts || "").slice(11, 16))}</td><td>${esc(e.kind === "activity" ? (ACT[e.ref] || e.ref) + ": " + ((e.meta || {}).text || "") : e.kind === "focus" ? ((e.meta || {}).text || "Fokusblock") : e.kind === "attendance" ? "Anwesenheit: " + e.ref : e.kind === "exam" ? e.ref + " " + e.value : "Known Error " + e.ref)}</td><td class="num">${e.minutes || ""}</td></tr>`).join("")}</table><div class="tiny muted" style="margin-top:6px">Dazu ${st.att} Fragen, ${st.cards} Karten (automatisch erfasst).</div>`;
  const es = exportStatus();
  $("#pendingInfo").innerHTML = `${pending.length} Einträge noch nicht vom Lauf übernommen` + (es ? ` · letzter Export ${esc(es.at)}: ${es.ok ? "<span class='status-ok'>OK (" + esc(es.msg) + ")</span>" : "<span class='status-warn'>FEHLER – " + esc(es.msg) + "</span>"}` : "");
  $("#syncState").textContent = fsHandle ? (es && !es.ok ? "Ordner verbunden · Export-Fehler" : "Ordner verbunden") : "nicht verbunden";
}
$("#logoutText").addEventListener("input", e => e.target.dataset.touched = "1");
$("#btnLogin").onclick = () => { addEvent("attendance", { ref: "login", exam: currentExamForAttendance() }); toast("Login erfasst – jetzt im Teams-Formular bestätigen"); };
$("#btnLogout").onclick = () => { $("#logoutText").dataset.touched = ""; const t = logoutText(); $("#logoutText").value = t; if (!t) return toast("Noch keine Einträge heute – erfasse zuerst Lernaktivitäten"); if (!EVENTS.find(e => e.date === TODAY && e.kind === "attendance" && e.ref === "logout")) addEvent("attendance", { ref: "logout", exam: currentExamForAttendance(), meta: { text: t } }); copy(t); autoExport(); };
$("#copyLogout").onclick = () => copy($("#logoutText").value);
$("#actAdd").onclick = () => { const t = $("#actText").value.trim(), ty = $("#actType").value, mi = +$("#actMin").value || 0; if (!t && ty === "other") return toast("Bitte kurz beschreiben"); addEvent("activity", { ref: ty, minutes: mi, exam: currentExamForAttendance(), meta: { text: t } }); $("#actText").value = ""; toast("Erfasst"); };
$("#absAdd").onclick = () => { addEvent("attendance", { ref: "absence", meta: { type: $("#absType").value, from: $("#absFrom").value, to: $("#absTo").value, note: $("#absNote").value.trim() } }); toast("Fehlzeit erfasst – bitte auch im Teams-Formular melden"); };

/* file system sync (Chrome/Edge: File System Access API; else download) */
let fsHandle = null;
const idb = (() => { let db; const open = () => new Promise((res, rej) => { if (db) return res(db); const r = indexedDB.open("xlrte", 1); r.onupgradeneeded = () => r.result.createObjectStore("kv"); r.onsuccess = () => res(db = r.result); r.onerror = () => rej(r.error); });
  return { get: k => open().then(d => new Promise(r => { const q = d.transaction("kv").objectStore("kv").get(k); q.onsuccess = () => r(q.result); q.onerror = () => r(null); })).catch(() => null),
           set: (k, v) => open().then(d => new Promise(r => { const t = d.transaction("kv", "readwrite"); t.objectStore("kv").put(v, k); t.oncomplete = r; t.onerror = r; })).catch(() => null) }; })();
idb.get("journalDir").then(h => { if (h) { fsHandle = h; renderJournalIfOpen(); if (pending.length) setTimeout(autoExport, 3000); } });
function renderJournalIfOpen() { if (state.view === "journal") renderJournal(); }
$("#fsConnect").onclick = async () => {
  if (!window.showDirectoryPicker) return toast("Dieser Browser kann keine Ordner verbinden – nutze „Jetzt exportieren“ (Download)");
  try { fsHandle = await window.showDirectoryPicker({ id: "xlrte-journal", mode: "readwrite" }); await idb.set("journalDir", fsHandle); toast("Verbunden: " + fsHandle.name); renderJournal(); } catch (e) { /* cancelled */ }
};
$("#fsExport").onclick = () => exportJournal(true);
/* Robust export (fix 26.09.2026): write → read back → parse → count check. Only a verified file counts as exported.
   Empty/partial files (seen on Google-Drive-for-desktop folders and when the tab closes mid-write) are retried under a new name;
   pending events stay in the browser until the daily run has merged them, so nothing is lost. */
let exporting = false, exportTimer = null;
const sleep = ms => new Promise(r => setTimeout(r, ms));
function exportStatus() { return LS.get("xlrte.exportStatus", null); }
function scheduleExport() { clearTimeout(exportTimer); exportTimer = setTimeout(autoExport, 60000); }
async function autoExport() { if (!fsHandle || !pending.length || exporting) return; try { if ((await fsHandle.queryPermission({ mode: "readwrite" })) === "granted") await exportJournal(false); } catch (e) { } }
async function writeVerified(name, body, n) {
  const fh = await fsHandle.getFileHandle(name, { create: true });
  const w = await fh.createWritable({ keepExistingData: false });
  await w.write(new Blob([body], { type: "application/json" })); await w.close();
  await sleep(500);
  const f = await (await fsHandle.getFileHandle(name)).getFile();
  let back = null; try { back = JSON.parse(await f.text()); } catch (e) { }
  if (!back || !Array.isArray(back.events) || back.events.length !== n) throw new Error(`Datei nach dem Schreiben unvollständig (${f.size} Bytes)`);
}
async function exportJournal(interactive) {
  if (!pending.length) { if (interactive) toast("Nichts Neues zu exportieren"); return; }
  if (exporting) { if (interactive) toast("Export läuft bereits …"); return; }
  exporting = true; clearTimeout(exportTimer);
  const snap = pending.slice(), n = snap.length;
  const body = JSON.stringify({ exported: new Date().toISOString(), app: "xlrte-cockpit-2", format: 2, count: n, events: snap }, null, 1);
  const stamp = () => `${localISO()}_${new Date().toTimeString().slice(0, 8).replace(/:/g, "")}`;
  let err = null;
  try {
    if (fsHandle) {
      let p = await fsHandle.queryPermission({ mode: "readwrite" }); if (p !== "granted" && interactive) p = await fsHandle.requestPermission({ mode: "readwrite" });
      if (p === "granted") {
        for (let i = 0; i < 3; i++) {
          try { await writeVerified(`${stamp()}${i ? "_r" + i : ""}_journal.json`, body, n); return ok(`${n} Einträge exportiert und geprüft`); }
          catch (e) { err = e; await sleep(1000 * (i + 1)); }
        }
      } else err = new Error("kein Schreibzugriff auf den Ordner");
    } else err = new Error("kein Ordner verbunden");
    if (interactive) {
      const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([body], { type: "application/json" })); a.download = `${stamp()}_journal.json`; a.click();
      return ok(`${n} Einträge als Download exportiert – Datei bitte nach _xlrte/journal/ verschieben`, true);
    }
    fail(err);
  } catch (e) { fail(e); }
  finally { exporting = false; renderJournalIfOpen(); }
  function ok(msg, dl = false) { const t = new Date().toLocaleString("de-DE"); LS.set("xlrte.lastExport", t); LS.set("xlrte.exportStatus", { ok: true, at: t, n, dl, msg: dl ? "Download" : "geprüft" }); toast(msg); }
  function fail(e) { const t = new Date().toLocaleString("de-DE"); LS.set("xlrte.exportStatus", { ok: false, at: t, n, msg: (e && e.message) || "unbekannt" }); toast("Export fehlgeschlagen: " + ((e && e.message) || "unbekannt") + " – Einträge bleiben gespeichert, bitte „Jetzt exportieren“"); }
}
function dayRollover() { const d = localISO(); if (d === TODAY) return; if (!run) { location.reload(); } else { TODAY = d; } }
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") autoExport(); else dayRollover(); });
setInterval(dayRollover, 5 * 60000);

/* ---------------------------------------------------------------- notebook */
function mdToHtml(md) {
  return esc(md).split("\n").map(l => l.startsWith("# ") ? `<h1>${l.slice(2)}</h1>` : l.startsWith("## ") ? `<h2>${l.slice(3)}</h2>` : l.startsWith("&gt; ") ? `<blockquote>${l.slice(5)}</blockquote>` : l.startsWith("- [ ] ") ? `<div>☐ ${l.slice(6)}</div>` : l.startsWith("- ") ? `<div>• ${l.slice(2)}</div>` : l ? `<p style="margin:4px 0">${l}</p>` : "").join("").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
}
function renderNotebook() {
  $("#nbLink").href = C.notebook_url || "https://notebooklm.google.com";
  const m = model(), dp = (C.day_plan || {})[TODAY] || {};
  $("#briefMd").innerHTML = D.briefing && D.briefing.markdown && D.today === TODAY ? mdToHtml(D.briefing.markdown) : `<p class="muted small">Das Briefing für heute erzeugt der tägliche Lauf (<code>_xlrte/notebooklm/${TODAY}_Briefing.md</code>). Bis dahin: Prompts rechts nutzen.</p>`;
  const focus = (dp.focus_los || []).join(", ") || m.weak.slice(0, 3).map(w => w.lo.id).join(", ");
  const inc = incidentBoard(); const probs = inc.prob.concat(inc.ke).map(x => x.lo + " " + loById(x.lo).text).slice(0, 5);
  const st = dayStats(TODAY);
  const lang = (bank().lang || (state.exam === "pmp" ? "en" : "de")) === "en";
  const P = [
    ["Audio-Briefing (morgens)", lang ? `Create a deep-dive audio overview based only on my sources for the PMP exam (ECO 2026). Focus today: ${focus}. Use PMI mindset reasoning ("what should the project manager do FIRST"), contrast predictive vs. agile answers, end with three typical traps.` : `Erstelle eine Audio-Zusammenfassung ausschließlich auf Basis meiner Quellen für die ITIL-5-Foundation-Prüfung. Schwerpunkt: Syllabus-Abschnitte ${focus}. Nenne jede offizielle Definition wörtlich, stelle typische Verwechslungen gegenüber und ende mit drei Prüfungsfallen. Zielgruppe: erfahrene IT-Führungskraft.`],
    ["Quiz im Notebook (Prüfungskaliber)", lang ? kalPrompt(focus) : `Stelle mir 10 Multiple-Choice-Fragen im PeopleCert-Stil (BL1/BL2, vier Optionen, eine richtig) zu ${focus}. Eine Frage nach der anderen, Lösung und Quelle erst nach meiner Antwort.`],
    ["Boss Fight & Buchungsreife (/bossfight)", lang ? "Review my current readiness and Boss Fight status from the latest learner profile." : "Prüfe meinen aktuellen Status in der 4-Stufen-Prüfungskaskade laut neuestem Lernprofil. Habe ich Schattenprüfung S1 und S2 absolviert? Wie sind meine Werte und welche konkrete Empfehlung gibst du mir für den nächsten Schritt vor der offiziellen Buchung?"],
    ["Recap (nach dem Logout)", `${lang ? "Summarize" : "Fasse"} ${lang ? "for my learning journal, based only on my sources:" : "für mein Lernjournal ausschließlich anhand meiner Quellen zusammen:"} ${probs.length ? (lang ? "my error patterns today: " : "meine heutigen Fehlerbilder: ") + probs.join("; ") + ". " : ""}${lang ? "Explain each one with the correct definition and a memorable contrast." : "Erkläre zu jedem die korrekte Definition und eine einprägsame Abgrenzung. Erzeuge danach 5 Karteikarten."} (${st.att} ${lang ? "questions today" : "Fragen heute"}, ${st.att ? Math.round(st.ok / st.att * 100) : 0} %)`]
  ];
  if (state.exam !== "itil5" && state.exam !== "pmp") {             // any other exam: neutral prompts in the pack's language
    const n = examCfg().name || state.exam;
    P.splice(0, 3,
      ["Audio-Briefing (morgens)", lang ? `Create an audio overview based only on my sources for the exam "${n}". Focus today: ${focus}. Contrast typical mix-ups and end with three exam traps.` : `Erstelle eine Audio-Zusammenfassung ausschließlich auf Basis meiner Quellen für die Prüfung „${n}“. Schwerpunkt heute: ${focus}. Stelle typische Verwechslungen gegenüber und ende mit drei Prüfungsfallen.`],
      ["Quiz im Notebook (Prüfungskaliber)", lang ? `Ask me 10 multiple-choice questions in the style of the exam "${n}" (four options, one correct) on ${focus}. One at a time; solution and source only after my answer.` : `Stelle mir 10 Multiple-Choice-Fragen im Stil der Prüfung „${n}“ (vier Optionen, eine richtig) zu ${focus}. Eine Frage nach der anderen, Lösung und Quelle erst nach meiner Antwort.`],
      ["Stand & Buchungsreife", lang ? "Check my status from the latest learner profile: how far am I from the pass mark, which three gaps cost the most points, and what is the next step before booking?" : "Prüfe meinen Stand laut neuestem Lernprofil: Wie weit bin ich von der Bestehensgrenze entfernt, welche drei Lücken kosten die meisten Punkte, und was ist der nächste Schritt vor der Buchung?"]);
  }
  const E = D.engine || {};
  if (E.full) P.unshift(["Lern-Engine „learn anything“ (einmalig: Notebook → Chat konfigurieren → Benutzerdefiniert)", E.full], ["Lern-Engine · Kurzfassung (falls das Feld begrenzt ist)", E.short]);
  if (D.profile) P.push(["Lernprofil heute (steht auch oben im Lernjournal – nach dem Lauf synchronisieren)", D.profile + (D.today !== TODAY ? `\n\n(Stand ${D.today} – der tägliche Lauf aktualisiert es)` : "")]);
  $("#prompts").innerHTML = P.map(([t, p], i) => `<div class="small" style="margin-top:8px"><b>${t}</b></div><div class="copybox"><p>${esc(p)}</p><button class="btn ghost sm" data-cp="${i}">Kopieren</button></div>`).join("");
  $$("#prompts [data-cp]").forEach(b => b.onclick = () => copy(P[+b.dataset.cp][1]));
}

/* ---------------------------------------------------------------- exams */
const CHECK = {
  itil5: ["PeopleCert-Voucher eingelöst", "Termin gebucht (deutsche Proctor-Slots sind knapp; kostenfrei verschiebbar bis 48 h vorher)", "Muttersprache-Frage bei der ersten Buchung geprüft (25 % Zeitverlängerung, falls Prüfungssprache weder Mutter- noch Arbeitssprache)", "ExamShield/Technik 24 h vorher getestet, kein zweiter Monitor", "Ausweis (wie im Account hinterlegt) bereit, Raum für 360°-Schwenk vorbereitet", "SP1 ≥ 80 %, SP2 ≥ 85 %", "Voucher-Ablaufdatum notiert (Verlängerung gegen Gebühr möglich)"],
  pmp: ["Moodle-Zugang für den Connected Classroom (ab 05.10.) funktioniert", "35 Contact Hours bescheinigt (nach Kurswoche)", "PMI-Mitgliedschaft (reduziert Prüfungsgebühr) entschieden", "PMI-Antrag eingereicht (Projekterfahrung dokumentiert) – Audit einkalkulieren", "Termin Pearson VUE (online oder Testcenter) gebucht; Umbuchen: bis 30 Tage vorher frei, danach 70 US$, ab 48 h vorher gar nicht (Handbuch Juni 2026)", "Name im PMI-Konto = Name im Ausweis (Original, nicht abgelaufen, Foto und Unterschrift); Namensänderung mindestens 5 Werktage vorher melden", "OnVUE-Systemtest auf demselben Gerät und im selben Netz wie am Prüfungstag, kein Firmen-Netz mit Firewall; Handy für Fotos von Raum und Schreibtisch bereit", "Prüfungstag: 30 Min vorher einchecken, über 15 Min Verspätung kein Zutritt; niemand sonst im Raum oder hörbar (sonst Abbruch als nicht bestanden)", "Zwei volle 180-Fragen-Simulationen im Prüfungskaliber (Fragen ab 40 Wörter) ≥ 75 %", "Pacing geübt: 180 Fragen (170 gewertet, 10 Pretest) in 240 Min, Fallblock zuerst, Pause 1 danach, Pause 2 etwa in der Mitte der Einzelfragen (nach einer Pause kein Zurück)"]
};
/* ---------------------------------------------------------------- Realistische Reife & Meilensteine */
/* Messungen: Prüfungs-Events der gewählten Prüfung; abgebrochene Läufe (< 80 % beantwortet) zählen nicht.
   Abschlag in Prozentpunkten (config exams.<x>.reality_discount_pp): eigene Sätze (XLRTE-…) vs. offizielle Muster – Startwerte aus ITIL (eigene Sätze 35–40/40, SP1/SP2 35/40, echt 33/40). */
function realityMeasures(events, exam, disc) {
  return events.filter(e => e.kind === "exam" && e.exam === exam).map(e => {
    const of = +((e.meta || {}).of) || 40, ans = (e.meta || {}).answered === undefined ? of : +(e.meta || {}).answered;
    if (ans < .8 * of) return null;
    const own = String(e.ref).startsWith("XLRTE-"), raw = Math.round(1000 * (+e.value) / of) / 10;
    return { ref: e.ref, date: e.date, raw, own, adj: Math.round((raw - (own ? disc.own : disc.official)) * 10) / 10 };
  }).filter(Boolean);
}
function realityLight(ms, target) {
  if (!ms.length) return { light: "none", prov: true, adj: null };
  const last = ms[ms.length - 1].adj, two = ms.length >= 2 ? ms.slice(-2) : null;
  const light = two && two.every(x => x.adj >= target) ? "green" : (last >= target - 5 || (two && two.some(x => x.adj >= target))) ? "yellow" : "red";
  return { light, prov: ms.length < 2, adj: last };
}
/* Meilensteine & Fallstricke: Daten in config.json → milestones. Fertig = Auto-Regel aus den Events, sonst manuell (Setting ms.<id>). */
function msDue(m, ex) {
  if (m.due) return m.due;
  if (m.due_rel !== undefined && ex && ex.target_date) { const d = new Date(ex.target_date + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + m.due_rel); return d.toISOString().slice(0, 10); }
  return null;
}
function msDone(m, ctx) {
  const a = m.auto || {};
  if (a.rule === "exam_pass") return ctx.events.some(e => e.kind === "exam" && e.ref === a.ref && isTrue((e.meta || {}).pass));
  if (a.rule === "exam_ref") return ctx.events.some(e => e.kind === "exam" && a.refs.includes(e.ref) && (!a.min_pct || 100 * (+e.value) / (+((e.meta || {}).of) || 40) >= a.min_pct));
  if (a.rule === "reality_green") return ctx.light === "green";
  return isTrue((ctx.set || {})["ms." + m.id]);
}
function msStatus(m, due, today, ctx) {
  if (msDone(m, ctx)) return "done";
  if (!due) return "open";
  const days = Math.round((new Date(due + "T12:00:00Z") - new Date(today + "T12:00:00Z")) / 864e5);
  return days < 0 ? "overdue" : days <= 7 ? "soon" : "open";
}
function renderReality(x) {
  const ex = examCfg(x), disc = ex.reality_discount_pp || { own: 10, official: 5 }, tgt = ex.target_pct || 75;
  const ms = realityMeasures(EVENTS, x, disc), r = realityLight(ms, tgt), m = model(x);
  const lamp = { none: ["Noch keine Messung", "var(--muted)"], red: ["Noch nicht bereit", "#c0392b"], yellow: ["Fast bereit", "#d68910"], green: ["Bereit", "var(--accent)"] }[r.light];
  const rows = ms.slice(-6).reverse().map(e => `<tr><td>${esc(e.date)}</td><td>${esc(e.ref)}</td><td class="num">${e.raw} %</td><td class="num">${e.adj} %</td></tr>`).join("");
  return `<div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border)"><div class="label" style="margin-bottom:6px">Realistische Reife${r.prov ? " · vorläufig" : ""}</div>
    <div class="row" style="gap:10px"><b style="color:${lamp[1]}">● ${lamp[0]}</b><span class="small muted">Modell-Prognose ${pct(m.pred / m.Q)} · realistisch (letzte Messung) ${r.adj === null ? "–" : r.adj + " %"} · Ziel ≥ ${tgt} % bei zwei Messungen in Folge</span></div>
    ${rows ? `<table style="margin-top:6px"><tr><th>Datum</th><th>Messung</th><th class="num">roh</th><th class="num">realistisch</th></tr>${rows}</table>` : ""}
    <div class="why" style="margin-top:6px">Abschlag: eigene Sätze −${disc.own}, offizielle Muster −${disc.official} Prozentpunkte. Startwerte aus nur einer echten Prüfung (ITIL); sie werden mit jeder Messung neu bewertet.</div></div>`;
}
function renderItilResult(x) {
  const res = (examCfg(x) || {}).result; if (!res) return "";
  const act = Math.round(1000 * res.score / res.of) / 10, last = ref => EVENTS.filter(e => e.kind === "exam" && e.exam === x && e.ref === ref).slice(-1)[0];
  const rows = ["XLRTE-S1", "XLRTE-S2", "XLRTE-S3", "XLRTE-S4", "SP1", "SP2"].map(ref => { const e = last(ref); if (!e) return ""; const p = Math.round(1000 * (+e.value) / ((+(e.meta || {}).of) || 40)) / 10; return `<tr><td>${esc(ref)}</td><td class="num">${p} %</td><td class="num">${p >= act ? "+" : ""}${Math.round((p - act) * 10) / 10}</td></tr>`; }).join("");
  return `<div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border)"><div class="label" style="margin-bottom:6px">Echtes Ergebnis ${esc(res.date)}</div>
    <div><b style="color:var(--accent)">✓ bestanden · ${res.score}/${res.of} (${act} %)</b> <span class="small muted">· Zertifikat gültig bis ${esc(res.valid_until || "–")}</span></div>
    ${res.topics ? `<div class="small muted" style="margin-top:4px">Schwächstes Thema: ${esc(res.topics.weakest)}</div>` : ""}
    <table style="margin-top:6px"><tr><th>Vorhersage</th><th class="num">roh</th><th class="num">Δ zu echt (Pkt.)</th></tr>${rows}</table>
    <div class="why" style="margin-top:6px">Modell-Prognose vor der Prüfung: ${esc(res.prediction || "–")}. Rohwerte der eigenen Sätze lagen darüber, das Modell dagegen nah dran.</div></div>`;
}
function renderMilestones() {
  const el = $("#msList"); if (!el) return;
  const set = settings(), today = TODAY, exs = examList();
  const light = realityLight(realityMeasures(EVENTS, "pmp", examCfg("pmp").reality_discount_pp || { own: 10, official: 5 }), examCfg("pmp").target_pct || 75).light;
  const ctx = { events: EVENTS, set, light };
  const rows = (C.milestones || []).map(m => { const due = msDue(m, examCfg(m.exam)); return Object.assign({}, m, { dueD: due, st: msStatus(m, due, today, ctx) }); })
    .sort((a, b) => (a.st === "done") - (b.st === "done") || (a.dueD || "9999").localeCompare(b.dueD || "9999"));
  const lab = { overdue: ["überfällig", "#c0392b"], soon: ["≤ 7 Tage", "#d68910"], open: ["offen", "var(--muted)"], done: ["✓ erledigt", "var(--accent)"] };
  const open = rows.filter(r => r.st !== "done").length;
  $("#msCount").textContent = `(${open} offen von ${rows.length})`;
  el.innerHTML = rows.map(m => { const auto = !!(m.auto && m.auto.rule), l = lab[m.st];
    return `<div class="row small" style="gap:8px;align-items:flex-start;flex-wrap:nowrap;padding:7px 0;border-bottom:1px solid var(--line);${m.st === "done" ? "opacity:.6" : ""}">
      <input type="checkbox" data-ms="${esc(m.id)}" data-msx="${esc(m.exam)}" ${m.st === "done" ? "checked" : ""} ${auto ? "disabled title='wird automatisch aus den Ergebnissen abgehakt'" : ""}>
      <div style="min-width:0;flex:1"><div>${m.type === "trap" ? "⚠ " : m.type === "gate" ? "◆ " : ""}<b>${esc(m.title)}</b>${m.critical ? " <span class='badge on'>kritisch</span>" : ""} <span class="muted">· ${m.exam === "pmp" ? "PMP" : "ITIL"}</span>${m.verify ? " <span class='muted' title='nicht bei PMI belegt, vor Verlass prüfen'>· prüfen</span>" : ""}</div>
      <div class="muted">${esc(m.note || "")}${m.source ? ` <i>(${esc(m.source)})</i>` : ""}</div></div>
      <div style="white-space:nowrap;text-align:right"><span style="color:${l[1]}">${l[0]}</span><br><span class="muted">${m.dueD ? esc(m.dueD) : "ohne Datum"}</span></div></div>`; }).join("") || `<div class="small muted">Keine Meilensteine hinterlegt.</div>`;
  $$("[data-ms]").forEach(i => i.onchange = () => { addEvent("setting", { exam: i.dataset.msx, ref: "ms." + i.dataset.ms, value: i.checked }); renderMilestones(); });
}
function renderExams() {
  const s = settings();
  $("#examCards").innerHTML = examList().map(x => { const ex = examCfg(x), m = model(x), d = dayDiff(TODAY, ex.target_date);
    return `<div class="card"><div class="label">${x === "pmp" ? "PMI · englisch · 180 Fragen (170 gewertet, 10 Pretest) / 240 Min" : x === "itil5" ? "PeopleCert · deutsch · 40 Fragen / 60 Min" : esc(ex.label || `${bank(x).questions || 40} Fragen / ${ex.sim_minutes || bank(x).minutes || 60} Min`)}</div><h3 style="margin:4px 0 8px">${esc(ex.name)}</h3>
      <div class="row small"><label>Zieltermin <input type="date" value="${ex.target_date}" data-td="${x}"></label><label class="row" style="gap:6px"><input type="checkbox" data-bk="${x}" ${ex.booked ? "checked" : ""}> gebucht</label><span class="muted">${d >= 0 ? d + " Tage" : ""}</span></div>
      <div class="kpis"><div class="kpi"><div class="v">${fmt1(m.pred)}/${m.Q}</div><div class="l">Prognose</div></div><div class="kpi"><div class="v">${pct(m.pPass)}</div><div class="l">Bestehen (Schätzung)</div></div><div class="kpi"><div class="v">${pct(m.cov)}</div><div class="l">Evidenzabdeckung</div></div></div>
      ${x === "itil5" ? `
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border)">
          <div class="label" style="margin-bottom:6px">Prüfungskaskade & Burn-Schutz</div>
          <div class="small" style="line-height:1.6">
            1. <b>Schattenprüfung S1</b>: ${s1Event() ? `<span style="color:var(--accent)">✓ ${s1Event().value}/40 Punkte (${Math.round(s1Event().value/40*100)} %)</span>` : "<span class='muted'>ungesehen · erster blinder Härtetest (Ziel ≥ 70 %)</span>"}<br>
            2. <b>Schattenprüfung S2</b>: ${s2Event() ? `<span style="color:var(--accent)">✓ ${s2Event().value}/40 Punkte (${Math.round(s2Event().value/40*100)} %)</span>` : "<span class='muted'>ungesehen · zweiter Härtetest vor Buchung (Ziel ≥ 75 %)</span>"}<br>
            3. <b>Offizielle SP1 (PeopleCert)</b>: ${EVENTS.filter(e => e.kind === "exam" && e.ref === "SP1").slice(-1)[0] ? `<span style="color:var(--accent)">✓ ${EVENTS.filter(e => e.kind === "exam" && e.ref === "SP1").slice(-1)[0].value}/40 Punkte</span>` : "<span class='muted'>geschützt · Kalibrierung vor Buchung (Ziel ≥ 80 %)</span>"}<br>
            4. <b>Offizielle SP2 (PeopleCert)</b>: ${EVENTS.filter(e => e.kind === "exam" && e.ref === "SP2").slice(-1)[0] ? `<span style="color:var(--accent)">✓ ${EVENTS.filter(e => e.kind === "exam" && e.ref === "SP2").slice(-1)[0].value}/40 Punkte</span>` : "<span class='muted'>geschützt · Generalprobe vor Examen (Ziel ≥ 85 %)</span>"}
          </div>
          ${(!s1Event() || !s2Event()) ? `<div class="why" style="margin-top:8px">Schutz aktiv: Erst S1 und S2 absolvieren, um die offiziellen Musterprüfungen nicht vorzeitig zu verbrennen.</div>` : `<div class="why" style="margin-top:8px;color:var(--accent)">S1 & S2 abgeschlossen – bereit für die offizielle PeopleCert-Kalibrierung!</div>`}
        </div>` : ""}${x === "itil5" ? renderItilResult(x) : renderReality(x)}${x === "pmp" && m.cov < .8 ? `<div class="why">Simulation erst ab ≈ 80 % Evidenzabdeckung einsetzen.</div>` : ""}</div>`; }).join("");
  $$("[data-td]").forEach(i => i.onchange = () => addEvent("setting", { ref: i.dataset.td + ".target_date", value: i.value }));
  $$("[data-bk]").forEach(i => i.onchange = () => addEvent("setting", { ref: i.dataset.bk + ".booked", value: i.checked }));
  const exs = EVENTS.filter(e => e.kind === "exam");
  $("#spList").innerHTML = exs.length ? `<table><tr><th>Datum</th><th>Prüfung</th><th class="num">Ergebnis</th><th></th></tr>${exs.slice().reverse().map(e => `<tr><td>${esc(e.date)}</td><td>${esc(e.ref)}</td><td class="num">${e.value}/${(e.meta || {}).of || 40} · ${Math.round(+e.value / ((e.meta || {}).of || 40) * 100)} %</td><td><button class="btn ghost sm" data-void="${esc(e.id)}" title="Fehleintrag entwerten">ungültig</button></td></tr>`).join("")}</table>` : `<div class="small muted">Noch keine Ergebnisse.</div>`;
  $$("[data-void]").forEach(b => b.onclick = () => { addEvent("setting", { ref: "void", value: b.dataset.void }); toast("Eintrag entwertet"); renderExams(); });
  renderMilestones(); renderStudyHall();
  const b1 = $("#btnLaunchSP1"), b2 = $("#btnLaunchSP2");
  if (b1) b1.onclick = () => { state.view = "training"; renderView(); startMode("sp1"); };
  if (b2) b2.onclick = () => { state.view = "training"; renderView(); startMode("sp2"); };
  const x = state.exam; $("#checklist").innerHTML = (CHECK[x] || (C.exams[x] || {}).checklist || ["Prüfungsprofil (Fragen, Zeit, Bestehensgrenze) beim Anbieter geprüft", "Termin gebucht und Zugangsdaten bereit", "Ausweis, Technik und Raum für den Prüfungstag geklärt", "Zwei Vollsimulationen über der Zielquote"]).map((t, i) => { const k = "chk." + x + "." + i; const on = isTrue(s[k]); return `<label class="row small" style="gap:8px;margin:6px 0;align-items:flex-start;flex-wrap:nowrap"><input type="checkbox" data-ck="${k}" ${on ? "checked" : ""}> <span>${esc(t)}</span></label>`; }).join("");
  $$("[data-ck]").forEach(c => c.onchange = () => addEvent("setting", { ref: c.dataset.ck, value: c.checked }));
}
$("#spAdd").onclick = () => { const w = $("#spWhich").value, sc = +$("#spScore").value, of = +$("#spOf").value || 40; if ($("#spScore").value.trim() === "" || !Number.isFinite(sc) || sc < 0 || sc > of) return toast("Bitte gültige Punktzahl eintragen (0 bis " + of + ")"); addEvent("exam", { ref: w, value: sc, meta: { of, pass: sc / of >= .65 } }); toast("Ergebnis gespeichert"); $("#spScore").value = ""; };


/* ---------------------------------------------------------------- PMI Study Hall (Erfassung, nur Zahlen) */
const SH_RATINGS = ["", "Above Target", "Target", "Below Target", "Needs Improvement"];
let shEdit = null;
function shRef(type, name) { const n = String(name || "").trim(); return type === "mini" ? "SH-MINI-" + String(parseInt(n, 10) || 0).padStart(2, "0") : type === "cat" ? "SH-CAT-" + (n || "x").slice(0, 40) : type === "full1" ? "SH-FULL1" : type === "full2" ? "SH-FULL2" : "SH-CUSTOM"; }
function shTaskRow(t = "", c = "", n = "") {
  const B = model("pmp").B, div = document.createElement("div"); div.className = "row small"; div.style.cssText = "gap:6px;margin:4px 0";
  div.innerHTML = `<select data-shT>${B.los.map(l => `<option value="${l.id}" ${l.id === t ? "selected" : ""}>${l.id} ${esc((l.text || "").slice(0, 40))}</option>`).join("")}</select><input data-shTc type="number" min="0" placeholder="richtig" style="width:70px" value="${c}"><input data-shTn type="number" min="1" placeholder="gesamt" style="width:70px" value="${n}"><button class="btn ghost sm" type="button">×</button>`;
  div.querySelector("button").onclick = () => div.remove(); $("#shTaskRows").appendChild(div);
}
function shCollect() {
  const type = $("#shType").value, ref = shRef(type, $("#shName").value), by_domain = {}, by_task = {}, rating = {};
  $$("#shDom [data-d]").forEach(r => { const d = r.dataset.d, c = r.querySelector("[data-c]").value, n = r.querySelector("[data-n]").value, rt = r.querySelector("[data-r]").value; if (n !== "") by_domain[d] = [+c || 0, +n]; if (rt) rating[d] = rt; });
  $$("#shTaskRows .row").forEach(r => { const n = r.querySelector("[data-shTn]").value; if (n !== "") by_task[r.querySelector("[data-shT]").value] = [+r.querySelector("[data-shTc]").value || 0, +n]; });
  const meta = { src: "studyhall", type: type === "full1" || type === "full2" ? "full" : type, of: +$("#shN").value };
  if (Object.keys(by_domain).length) meta.by_domain = by_domain; if (Object.keys(by_task).length) meta.by_task = by_task; if (Object.keys(rating).length) meta.rating = rating;
  const note = $("#shNote").value.trim().slice(0, 200); if (note) meta.note = note;
  return { ref, value: +$("#shC").value, minutes: +$("#shMin").value || 0, date: $("#shDate").value || TODAY, meta, errs: shValidate({ of: $("#shN").value, value: $("#shC").value, by_domain, by_task }) };
}
function renderStudyHall() {
  if (!$("#shCard")) return;
  const ex = examCfg("pmp"), B = model("pmp").B, evs = shValid(EVENTS, "pmp").slice().sort((a, b) => (a.date + a.ts).localeCompare(b.date + b.ts));
  if (!$("#shDom").children.length) $("#shDom").innerHTML = B.categories.map(c => `<div data-d="${c.id}">${esc(c.name)}: <input data-c type="number" min="0" placeholder="r" style="width:50px"> / <input data-n type="number" min="1" placeholder="n" style="width:50px"> <select data-r>${SH_RATINGS.map(r => `<option>${r}</option>`).join("")}</select></div>`).join("");
  if (!$("#shDate").value) $("#shDate").value = TODAY;
  [["full1", "SH-FULL1"], ["full2", "SH-FULL2"]].forEach(([k, ref]) => { const o = $("#shType").querySelector(`[value=${k}]`), d = shProtectDate(ref, ex); o.textContent = `Full-Length ${k.slice(-1)}` + (d && TODAY < d ? ` (geschützt bis ${d.split("-").reverse().slice(0, 2).join(".")}.)` : ""); });
  const full = evs.filter(e => e.ref === "SH-FULL1" || e.ref === "SH-FULL2");
  const prot = ["SH-FULL1", "SH-FULL2"].map(ref => { const d = shProtectDate(ref, ex), done = full.find(e => e.ref === ref); return done ? "" : d && TODAY < d ? `<div class="small">🔒 Full-Length ${ref.slice(-1)}: geschützt – erst ab ${esc(d)}. Die Fragen vorher nicht ansehen.</div>` : d ? `<div class="small">Full-Length ${ref.slice(-1)} ist freigegeben (seit ${esc(d)}).</div>` : ""; }).join("");
  const cal = full.map(e => { const of = (e.meta || {}).of || 180, prev = new Date(e.date + "T12:00:00Z"); prev.setUTCDate(prev.getUTCDate() - 1); const m = model("pmp", prev.toISOString().slice(0, 10)), sc = e.value / of * m.Q, d = sc - m.pred;
    return `<div class="small">Study Hall ${esc(e.ref.replace("SH-FULL", "Full "))}: <b>${e.value}/${of}</b> (${Math.round(e.value / of * 100)} %) am ${esc(e.date)} · Prognose am Vortag ${fmt1(m.pred)}/${m.Q} · Differenz <b>${d >= 0 ? "+" : ""}${fmt1(d)}</b> Punkte (auf ${m.Q} umgerechnet)</div>`; }).join("");
  $("#shCalib").innerHTML = prot + cal;
  $("#shList").innerHTML = evs.length ? `<table class="small"><tr><th>Datum</th><th>Ref</th><th class="num">Ergebnis</th><th>Domänen / Tasks</th><th></th></tr>${evs.slice().reverse().map(e => { const m = e.meta || {}, dom = Object.entries(m.by_domain || {}).map(([d, v]) => `${d} ${v[0]}/${v[1]}${(m.rating || {})[d] ? " (" + esc(m.rating[d]) + ")" : ""}`).join(", "), tk = Object.entries(m.by_task || {}).map(([t, v]) => `${t} ${v[0]}/${v[1]}`).join(", ");
    return `<tr><td>${esc(e.date)}</td><td>${esc(e.ref)}</td><td class="num">${e.value}/${m.of} · ${Math.round(e.value / m.of * 100)} %</td><td>${esc([dom, tk].filter(Boolean).join(" · ")) || '<span class="muted">nur Gesamtwert (kein Mastery-Beleg)</span>'}</td><td><button class="btn ghost sm" data-shfix="${esc(e.id)}">Korrigieren</button></td></tr>`; }).join("")}</table>` : '<div class="small muted">Noch keine Study-Hall-Ergebnisse erfasst.</div>';
  $$("[data-shfix]").forEach(b => b.onclick = () => { const e = EVENTS.find(x => x.id === b.dataset.shfix); if (!e) return; const m = e.meta || {};
    $("#shType").value = e.ref === "SH-FULL1" ? "full1" : e.ref === "SH-FULL2" ? "full2" : m.type || "custom"; $("#shName").value = e.ref.replace(/^SH-(MINI-|CAT-)/, "").replace(/^0+/, ""); $("#shDate").value = e.date; $("#shC").value = e.value; $("#shN").value = m.of; $("#shMin").value = e.minutes || ""; $("#shNote").value = m.note || "";
    $$("#shDom [data-d]").forEach(r => { const v = (m.by_domain || {})[r.dataset.d]; r.querySelector("[data-c]").value = v ? v[0] : ""; r.querySelector("[data-n]").value = v ? v[1] : ""; r.querySelector("[data-r]").value = (m.rating || {})[r.dataset.d] || ""; });
    $("#shTaskRows").innerHTML = ""; Object.entries(m.by_task || {}).forEach(([t, v]) => shTaskRow(t, v[0], v[1])); shEdit = e.id; $("#shMsg").textContent = "Korrektur: Speichern entwertet den alten Eintrag und legt den neuen an."; $("#shCard details").open = true; });
}
$("#shAddTask").onclick = () => shTaskRow();
$("#shSave").onclick = () => {
  const f = shCollect(); if (f.errs.length) { $("#shMsg").textContent = f.errs.join(" · "); return; }
  const prot = f.ref === "SH-FULL1" || f.ref === "SH-FULL2" ? shProtectDate(f.ref, examCfg("pmp")) : null; if (prot && f.date < prot && !shEdit) toast("Hinweis: Full-Length war bis " + prot + " geschützt");
  if (shEdit) { addEvent("ext_void", { exam: "pmp", ref: shEdit, value: "" }); shEdit = null; }
  addEvent("ext", { exam: "pmp", ref: f.ref, value: f.value, minutes: f.minutes, date: f.date, meta: f.meta });
  $("#shMsg").textContent = ""; ["#shC", "#shN", "#shMin", "#shNote", "#shName"].forEach(i => $(i).value = ""); $$("#shDom input").forEach(i => i.value = ""); $("#shTaskRows").innerHTML = ""; toast("Study-Hall-Ergebnis gespeichert"); renderExams();
};
/* ---------------------------------------------------------------- focus dock */
const dock = { left: 0, total: 0, t: null, started: 0 };
function dockRender() { const s = dock.t ? dock.left : (+$("#dockLen").value) * 60; $("#dockClock").textContent = Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); $("#dockMode").textContent = $("#dockLen").value === "20" ? "Pause (NSDR/Bewegung)" : "Fokusblock"; }
$("#dockLen").onchange = dockRender;
$("#dockBtn").onclick = () => {
  if (dock.t) { clearInterval(dock.t); dock.t = null; const mins = Math.round((Date.now() - dock.started) / 60000); if ($("#dockLen").value !== "20" && mins >= 5) { addEvent("focus", { minutes: mins, ref: "focus", meta: { text: `Fokusblock ${mins} Min` } }); toast(`${mins} Fokusminuten erfasst`); } $("#dockBtn").textContent = "Start"; dockRender(); return; }
  dock.total = (+$("#dockLen").value) * 60; dock.left = dock.total; dock.started = Date.now(); $("#dockBtn").textContent = "Stopp";
  dock.t = setInterval(() => { dock.left = dock.total - Math.floor((Date.now() - dock.started) / 1000); if (dock.left <= 0) { clearInterval(dock.t); dock.t = null; const mins = Math.round(dock.total / 60); if ($("#dockLen").value !== "20") addEvent("focus", { minutes: mins, ref: "focus", meta: { text: `Fokusblock ${mins} Min` } }); $("#dockBtn").textContent = "Start"; toast($("#dockLen").value === "20" ? "Pause vorbei – nächster Block" : "Block beendet – 20 Min offline pausieren"); try { new (window.AudioContext || window.webkitAudioContext)().resume(); } catch (e) { } } dockRender(); }, 1000);
};

/* ---------------------------------------------------------------- tooltips & render */
document.addEventListener("mousemove", e => { const t = e.target.closest("[data-tip]"); const tip = $("#tip"); if (!t) { if (!e.target.closest("#evmHit")) tip.style.display = "none"; return; } tip.textContent = t.dataset.tip; tip.style.display = "block"; tip.style.left = Math.min(e.clientX + 12, innerWidth - 320) + "px"; tip.style.top = e.clientY + 14 + "px"; });
function renderView() {
  const v = state.view;
  if (v === "cockpit") renderCockpit(); else if (v === "pfad") renderPfad(); else if (v === "training") { if (!run) renderTrainingMenu(); } else if (v === "fehler") renderBoard();
  else if (v === "projekt") renderEVM(); else if (v === "journal") renderJournal(); else if (v === "notebook") renderNotebook(); else if (v === "pruefung") renderExams();
}
function renderAll() { renderHeader(); renderView(); }
renderAll(); dockRender();
/* no export on beforeunload: an async write cut off by closing the tab leaves a 0-byte file (root cause of the empty journal exports up to 26.09.2026). Pending events persist in localStorage and are exported on next open / when the tab is hidden. */
