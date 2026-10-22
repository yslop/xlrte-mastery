#!/usr/bin/env python3
"""XLRTE core bank — PMP (ECO 2026), EN. Situational items in PMI mindset.
Legacy seed B (pm_001–pm_034, never renumber: events reference these ids) + wave-1 modules
(bank_pmp_people / _process / _be / _cases, see bank_pmp_common for the format).
APPEND ONLY: new items go to the END of their module's ITEMS list. Ids are module-scoped (pm_p### people, pm_r### process,
pm_b### business environment, pm_c### cases), so appending never renumbers other modules. tests/bank_ids.json freezes id → question.
Legacy tuple: (task, bl, type, question, [A,B,C,D], answer_index, why)
Build: python3 scripts/bank_pmp.py -> data/items_pmp.json + data/cases_pmp.json
"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank_pmp_people, bank_pmp_process, bank_pmp_be, bank_pmp_cases

B = [
("P.1",2,"std","At kickoff, team members describe the project's purpose in very different ways. What should the project manager do FIRST?",
 ["Escalate to the sponsor to restate the business case","Facilitate a session to co-create a shared vision and success criteria","Issue a detailed scope statement for sign-off","Replace team members who are not aligned"],1,
 "Develop a common vision: co-create it with the team; alignment before documentation."),
("P.2",2,"std","Two senior developers disagree on the architecture and the conflict is slowing the sprint. What should the project manager do FIRST?",
 ["Escalate to the functional manager","Decide on the architecture to save time","Meet with both to understand the root cause and collaborate on a solution","Ask the product owner to choose"],2,
 "PMI mindset: address conflict early, privately, collaborate/problem-solve before escalating."),
("P.2",1,"std","Which conflict resolution technique generally produces a lasting win-win outcome?",
 ["Smoothing/accommodating","Forcing/directing","Collaborating/problem solving","Withdrawing/avoiding"],2,"Collaborate/problem-solve addresses the root cause."),
("P.3",2,"std","In an agile team, the project manager acts as a servant leader. Which action fits BEST?",
 ["Assigning tasks daily to each developer","Removing impediments and shielding the team from distractions","Approving each user story before work begins","Reporting individual velocity to HR"],1,"Servant leadership: remove impediments, enable self-organization."),
("P.3",2,"std","A newly formed team is polite but hesitant and relies heavily on the project manager. Which Tuckman stage is this?",
 ["Forming","Storming","Norming","Performing"],0,"Forming: orientation, dependence on leader."),
("P.4",2,"std","A key stakeholder with high power has been disengaged and now objects to deliverables late in the project. What should have prevented this?",
 ["A stricter change control board","Early stakeholder identification, analysis and ongoing engagement","A larger contingency reserve","More detailed WBS"],1,"Engage stakeholders: identify and analyze early, engage continuously."),
("P.5",2,"std","The customer and the team interpret 'done' differently for a feature. What should the project manager do?",
 ["Let the team decide","Align on explicit acceptance criteria and a shared definition of done","Raise a change request","Escalate to the sponsor"],1,"Align expectations with explicit, shared criteria."),
("P.6",2,"std","Stakeholder expectations are drifting as the market changes. What is the BEST ongoing practice?",
 ["Freeze the scope","Hold regular reviews/demos and feedback loops to manage expectations","Reduce communication to avoid new requests","Update the charter monthly"],1,"Manage expectations continuously via feedback loops."),
("P.7",2,"std","A key expert will leave the project next month. What should the project manager do FIRST to protect project knowledge?",
 ["Request a replacement from HR","Plan knowledge transfer, e.g., pairing and capturing tacit knowledge","Update the risk register only","Delay the expert's departure"],1,"Help ensure knowledge transfer: explicit AND tacit knowledge."),
("P.8",1,"std","A team grows from 6 to 10 members. How many additional communication channels are created?",
 ["4","15","30","45"],2,"n(n-1)/2: 6 → 15, 10 → 45; difference 30."),
("PR.1",2,"std","The organization requires phase gates, but requirements for the user interface are expected to evolve. Which approach fits BEST?",
 ["Purely predictive","Purely agile","Hybrid: predictive governance with iterative delivery for the evolving parts","Kanban only"],2,"Tailor the delivery approach to context — hybrid."),
("PR.2",2,"std","A developer adds an extra feature the customer did not request because it seemed useful. This is:",
 ["Scope creep","Gold plating","Fast tracking","Progressive elaboration"],1,"Gold plating = unrequested extras; avoid it."),
("PR.2",1,"std","Which document describes each work package in detail, including acceptance criteria and responsible organization?",
 ["WBS dictionary","Project charter","Scope management plan","Requirements traceability matrix"],0,"WBS dictionary details each WBS component."),
("PR.3",2,"std","With limited budget, which approach maximizes value delivery?",
 ["Deliver all features at the end","Prioritize by value and deliver incrementally, starting with an MVP","Deliver the easiest features first","Let each team pick its favorite features"],1,"Value-based delivery: prioritize and deliver incrementally."),
("PR.4",2,"std","Resource leveling on the critical path will MOST likely:",
 ["Shorten the schedule","Extend the schedule","Have no effect on the schedule","Reduce quality"],1,"Leveling can change the critical path and extend the end date; smoothing stays within float."),
("PR.5",2,"std","The scope is unclear and the buyer wants to start work quickly. Which contract type is MOST appropriate?",
 ["Firm fixed price","Time and materials","Fixed price incentive fee","Fixed price with economic price adjustment"],1,"T&M suits unclear scope; FFP puts risk on seller and needs clear scope."),
("PR.5",1,"std","Which contract type places the MOST cost risk on the seller?",
 ["Cost plus fixed fee","Time and materials","Firm fixed price","Cost plus award fee"],2,"FFP: seller bears cost overruns."),
("PR.6",1,"std","PV = 500k, EV = 450k, AC = 520k. Which statement is correct?",
 ["Ahead of schedule, under budget","Behind schedule, over budget","Behind schedule, under budget","Ahead of schedule, over budget"],1,"SPI = 450/500 = 0.90 (<1 behind); CPI = 450/520 ≈ 0.87 (<1 over budget)."),
("PR.6",1,"std","BAC = 200k, CPI = 0.8. If current performance continues, what is the EAC?",
 ["160k","200k","250k","240k"],2,"EAC = BAC / CPI = 200 / 0.8 = 250k."),
("PR.6",1,"std","Which reserve is used for 'unknown-unknowns' and is NOT part of the cost baseline?",
 ["Contingency reserve","Management reserve","Buffer","Float"],1,"Management reserve is outside the cost baseline; contingency covers known-unknowns within it."),
("PR.7",2,"std","A defect is found by the customer after release. In cost of quality terms this is a:",
 ["Prevention cost","Appraisal cost","Internal failure cost","External failure cost"],3,"Found by customer after delivery → external failure."),
("PR.8",1,"std","Activity ES = 10, LS = 14. What is its total float and is it critical?",
 ["4 days, not critical","0 days, critical","14 days, not critical","4 days, critical"],0,"Float = LS - ES = 4; critical path activities have zero float."),
("PR.8",2,"std","To shorten the schedule WITHOUT adding cost, the project manager should consider:",
 ["Crashing","Fast tracking","Adding resources","Reducing quality"],1,"Fast tracking overlaps activities (adds risk, not direct cost); crashing adds resources/cost."),
("PR.9",2,"std","A sprint burndown chart shows the line flat for the first half of the sprint. What should the project manager do FIRST?",
 ["Cancel the sprint","Investigate with the team whether work is blocked or not being updated","Add team members","Extend the sprint"],1,"Evaluate status: investigate before acting."),
("PR.10",2,"std","The customer has accepted the final deliverable. What should the project manager do NEXT?",
 ["Release the team immediately","Complete administrative closure: close contracts, archive, lessons learned, transition benefits","Start the next project","Send the final invoice only"],1,"Manage closure: formal closure activities."),
("BE.1",2,"std","Decision rights are unclear, causing delays whenever a trade-off must be made. What should the project manager do?",
 ["Make all decisions personally","Define governance: decision rights, escalation paths and thresholds with the sponsor","Wait for the steering committee","Log it as a risk"],1,"Define and establish project governance."),
("BE.2",2,"std","A new data-protection regulation affects the product under development. What should the project manager do FIRST?",
 ["Continue as planned","Assess the compliance impact with the relevant experts and plan required changes","Stop the project","Inform customers"],1,"Plan and manage compliance: assess impact first."),
("BE.3",2,"std","In a predictive project, a stakeholder asks a team member directly for a small change. What should happen?",
 ["The team member implements it if it is small","The request goes through integrated change control with impact analysis","The project manager rejects it","The sponsor decides informally"],1,"All changes go through the change control process; assess impact before deciding."),
("BE.4",2,"std","The team reports that a dependency on another department blocks progress. What should the project manager do?",
 ["Tell the team to find a workaround themselves","Actively work to remove the impediment and log it in the issue log","Escalate immediately to the executive board","Re-baseline the schedule"],1,"Remove impediments and manage issues — servant leader acts."),
("BE.5",1,"std","A risk has a 30 % probability and an impact of -50k. What is its expected monetary value?",
 ["-15k","-50k","-35k","15k"],0,"EMV = P × I = 0.3 × -50k = -15k."),
("BE.5",2,"std","Buying insurance against a risk is an example of which response strategy?",
 ["Avoid","Mitigate","Transfer","Accept"],2,"Transfer shifts impact/ownership to a third party."),
("BE.6",2,"std","After each iteration, the team identifies improvements but rarely implements them. What should the project manager do?",
 ["Stop holding retrospectives","Make improvement actions visible, prioritize a few, and track them in the next iteration","Assign improvements to the PMO","Add improvements to the risk register"],1,"Continuous improvement requires follow-through."),
("BE.7",2,"std","End users are resisting a new system that the project delivers. What is the BEST approach?",
 ["Mandate usage through management","Support organizational change: assess readiness, involve users, communicate benefits, train","Delay the release indefinitely","Reduce scope"],1,"Support organizational change (e.g., ADKAR, Kotter)."),
("BE.8",2,"std","A competitor releases an AI feature that changes customer expectations mid-project. What should the project manager do?",
 ["Ignore it to protect scope","Evaluate the impact with the product owner/sponsor and adapt the backlog or plan through the proper process","Immediately add the feature","Cancel the project"],1,"Evaluate external environment changes, then adapt through governance."),
]


# legacy items: approach + ECO enabler (texts unchanged)
EXTRA_LEGACY = {
 "pm_001": ("hybrid", "P.1.1"), "pm_002": ("agile", "P.2.2"), "pm_003": ("predictive", "P.2.3"), "pm_004": ("agile", "P.3.2"),
 "pm_005": ("predictive", "P.3.1"), "pm_006": ("predictive", "P.4.1"), "pm_007": ("agile", "P.5.2"), "pm_008": ("agile", "P.6.2"),
 "pm_009": ("hybrid", "P.7.1"), "pm_010": ("predictive", "P.8.1"), "pm_011": ("hybrid", "PR.1.2"), "pm_012": ("predictive", "PR.2.1"),
 "pm_013": ("predictive", "PR.2.3"), "pm_014": ("agile", "PR.3.3"), "pm_015": ("predictive", "PR.4.2"), "pm_016": ("predictive", "PR.5.3"),
 "pm_017": ("predictive", "PR.5.3"), "pm_018": ("predictive", "PR.6.6"), "pm_019": ("predictive", "PR.6.5"), "pm_020": ("predictive", "PR.6.7"),
 "pm_021": ("predictive", "PR.7.5"), "pm_022": ("predictive", "PR.8.5"), "pm_023": ("predictive", "PR.8.8"), "pm_024": ("agile", "PR.9.5"),
 "pm_025": ("predictive", "PR.10.4"), "pm_026": ("hybrid", "BE.1.3"), "pm_027": ("hybrid", "BE.2.6"), "pm_028": ("predictive", "BE.3.1"),
 "pm_029": ("hybrid", "BE.4.3"), "pm_030": ("predictive", "BE.5.2"), "pm_031": ("predictive", "BE.5.6"), "pm_032": ("agile", "BE.6.1"),
 "pm_033": ("hybrid", "BE.7.2"), "pm_034": ("agile", "BE.8.2"),
}


def place(iid, it):
    """Deterministic shuffle per id: correct option(s) are written first in the modules."""
    idx = list(range(len(it["opts"])))
    random.Random(iid).shuffle(idx)
    opts = [it["opts"][i] for i in idx]
    right = sorted(idx.index(k) for k in range(it["k"]))
    return opts, (right if it["type"] == "multi" else right[0])


def jwrite(name, obj):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", name)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def build():
    out = []
    for n, (lo, bl, typ, q, opts, ans, why) in enumerate(B, 1):
        iid = f"pm_{n:03d}"
        appr, en = EXTRA_LEGACY[iid]
        out.append({"id": iid, "exam": "pmp", "lo": lo, "bl": bl, "type": typ, "q": q, "options": opts,
                    "answer": ans, "why": why, "src": "xlrte-core", "status": "approved", "appr": appr, "en": en})
    for mod, pre in ((bank_pmp_people, "p"), (bank_pmp_process, "r"), (bank_pmp_be, "b"), (bank_pmp_cases, "c")):
        for n, it in enumerate(mod.ITEMS, 1):
            iid = f"pm_{pre}{n:03d}"
            opts, ans = place(iid, it)
            row = {"id": iid, "exam": "pmp", "lo": it["en"].rsplit(".", 1)[0], "bl": 2, "type": it["type"], "q": it["q"],
                   "options": opts, "answer": ans, "why": it["why"], "src": "xlrte-core", "status": "approved",
                   "appr": it["appr"], "en": it["en"]}
            if it.get("case"):
                row["case"] = it["case"]
            out.append(row)
    jwrite("items_pmp.json", out)
    jwrite("cases_pmp.json", bank_pmp_cases.CASES)
    print(len(out), "PMP items ·", len(bank_pmp_cases.CASES), "cases")


if __name__ == "__main__":
    build()
