"""PMP case/scenario sets (ECO 2026 'Case or Scenario' item type). Each case has 3–4 questions."""
from bank_pmp_common import S, M

CASES = [
 {"id": "case_01", "title": "Hybrid core-banking release",
  "text": "You lead a 14-month project to replace the payments module of a mid-sized bank. The organisation mandates phase gates and "
          "a formal change control board (CCB). Interfaces to the regulator's reporting system are fixed by law; the customer-facing "
          "mobile features are expected to evolve based on user feedback. Two months in, internal audit announces a new requirement: "
          "all personal data processed by the module must be encrypted at rest before go-live. The sponsor, compliance officer, "
          "an agile delivery team (8 people) and a vendor for the regulator interface are involved."},
 {"id": "case_02", "title": "Vendor slipping on critical hardware",
  "text": "A logistics project depends on a vendor delivering 40 handheld scanners under a firm-fixed-price contract. The delivery date "
          "is on the critical path. Three weeks before the date, the vendor reports that a component shortage will delay delivery by "
          "four weeks. The contract includes a liquidated-damages clause. The warehouse team is ready to start training, and the "
          "operations manager is pressing for a go-live before the peak season."},
 {"id": "case_03", "title": "Midpoint budget review",
  "text": "A predictive infrastructure project has a budget at completion (BAC) of 800,000. At the end of month 6 of 12 the status is: "
          "planned value 400,000; earned value 320,000; actual cost 400,000. The overrun was caused mainly by a supplier price increase "
          "that is expected to persist. The governance framework requires escalation to the steering committee when CPI or SPI falls "
          "below 0.9.",
  "table": [["Metric", "Value"], ["BAC", "800,000"], ["PV", "400,000"], ["EV", "320,000"], ["AC", "400,000"]]},
 {"id": "case_04", "title": "AI assistant for customer service",
  "text": "Your project introduces a generative-AI assistant that drafts answers for 200 customer-service agents in the EU. The data "
          "science team wants to train it on historic support tickets, some of which contain personal data. The legal department "
          "points to the EU AI Act and GDPR. A competitor has just launched a similar tool, and marketing wants to accelerate the release."},
 {"id": "case_05", "title": "Two teams become one",
  "text": "After a merger, two development teams (one from each company) must deliver a joint product. Team A works in two-week sprints; "
          "team B is used to detailed task assignments from its manager. In the first joint planning session, two senior engineers "
          "argue openly about the architecture and several team B members stay silent. Employees are also worried about job security "
          "after the merger."},
 {"id": "case_06", "title": "Sustainable office building",
  "text": "You manage the construction of a new office building. The client's contract requires a recognised green-building "
          "certification and a 30 % reduction in embodied carbon versus a reference design. Midway, the structural subcontractor proposes "
          "a cheaper concrete mix with a higher carbon footprint. The facility manager who will operate the building has not been "
          "involved so far."},
 {"id": "case_07", "title": "Falling velocity",
  "text": "An agile team of seven builds a customer portal. Velocity over the last four sprints: 42, 38, 31, 27 story points. In the "
          "retrospectives the team repeatedly mentions waiting for approvals from the security department and unclear acceptance "
          "criteria, but action items are rarely completed. The product owner is under pressure to deliver the release on time.",
  "table": [["Sprint", "Committed", "Done"], ["5", "44", "42"], ["6", "42", "38"], ["7", "40", "31"], ["8", "38", "27"]]},
 {"id": "case_08", "title": "ERP go-live under resistance",
  "text": "A company is replacing its 20-year-old ERP system. Technical acceptance tests passed, but the finance department's head "
          "openly doubts the new system and many accountants still use their old spreadsheets in parallel. Go-live is in six weeks. "
          "The operations support team says it has not received the documentation it needs to run the new system."},
 {"id": "case_09", "title": "Closing a research project",
  "text": "A two-year product research project is ending. Two of the three senior researchers leave the company next month. Most "
          "insights exist only in their heads and in scattered chat messages. The sponsor wants a quick close so the budget can be "
          "reallocated, and a supplier still has an open invoice dispute."},
 {"id": "case_10", "title": "Regulation changes the market",
  "text": "Your team is building a subscription app. Halfway through the release plan, a new consumer-protection law requires a one-click "
          "cancellation option and a clear price display before any purchase. The law takes effect in four months. The backlog is "
          "full of features requested by marketing, and some team members see the law as a distraction from 'the real product'."},
 {"id": "case_11", "title": "Schedule crunch before a trade fair",
  "text": "A product must be ready for a trade fair in 10 weeks; the current schedule forecasts 12 weeks. The critical path runs through "
          "design (3 weeks), prototyping (4 weeks) and testing (5 weeks). A senior engineer could be borrowed from another project "
          "for four weeks. Testing could partly overlap with prototyping, although the test lead warns about rework.",
  "table": [["Activity", "Duration", "Float"], ["Design", "3 w", "0"], ["Prototyping", "4 w", "0"], ["Testing", "5 w", "0"],
            ["Marketing material", "4 w", "6 w"]]},
]

ITEMS = [
 # case_01
 S("PR.1.2", "hybrid", "Which delivery approach fits this project BEST?",
   ["Hybrid: predictive governance and regulator interface, iterative delivery for the mobile features",
    "Fully predictive, because the bank mandates phase gates and a formal change control board for all work", "Fully agile for all parts, because user feedback on the mobile features is the most important success factor",
    "Kanban for all work streams, including the regulator interface, to maximise flow and minimise planning overhead"],
   "Stable, legally fixed parts suit predictive planning; evolving features suit iterations. Purely predictive ignores the evolving requirements.", "case_01"),
 S("BE.2.6", "hybrid", "How should the project manager respond to the new encryption requirement FIRST?",
   ["Analyse its impact with compliance and the team, then submit a change request with options",
    "Add it to the backlog as a normal story and let the product owner prioritise it against the mobile features", "Ask the vendor to implement encryption within the current contract, since security is part of good practice",
    "Plan it for a release after go-live, because the requirement came late and the current plan is baselined"],
   "A compliance requirement must be assessed and routed through change control. Treating it as optional backlog work risks noncompliance.", "case_01"),
 M("BE.3.1", "hybrid", "The CCB approves the encryption change. Which actions should follow?",
   ["Update the affected baselines and plans", "Communicate the decision and its impact to stakeholders"],
   ["Close the change log entry without further action", "Let the team decide individually how to encrypt data", "Reduce testing to keep the date"],
   "Approved changes are implemented, baselines/documents updated and the status communicated. Cutting testing creates quality and compliance risk.", "case_01"),
 S("P.8.4", "predictive", "The regulator's reporting requirements must be reflected in project communication. Where should this be defined?",
   ["In the communications management plan, including frequency, format and responsible roles",
    "In the team charter, so the team knows its reporting obligations toward the regulator", "Only in the vendor contract, because the vendor builds the regulator interface", "In the definition of done for each sprint of the agile delivery team"],
   "Reporting requirements belong in the communications management plan. The team charter covers team working agreements, not external reporting.", "case_01"),
 # case_02
 S("PR.5.8", "predictive", "What should the project manager do FIRST after the vendor's notice?",
   ["Review the contract terms and meet the vendor to understand options for recovering the date",
    "Terminate the contract for default and select an alternative vendor to protect the go-live date", "Apply the liquidated-damages clause immediately so the vendor feels the financial consequence", "Order scanners from another vendor right away and cancel the original order later if needed"],
   "Understand the situation and contractual options before acting. Terminating or penalising first damages the relationship and may not solve the delay.", "case_02"),
 S("BE.4.1", "predictive", "Which analysis is MOST important before deciding how to respond to the delay?",
   ["Assess the impact of the four-week delay on the critical path, training and the go-live date",
    "Analyse the vendor's financial situation to judge whether the vendor is at risk of insolvency", "Update the lessons learned register with the causes of the vendor's component shortage", "Review the procurement strategy to decide whether future contracts should use another type"],
   "The impediment's impact on schedule and objectives drives the response. Lessons learned are useful later but do not inform the immediate decision.", "case_02"),
 S("PR.8.8", "predictive", "Which option could reduce the schedule impact WITHOUT changing the vendor contract?",
   ["Re-sequence work so training starts with a small number of loaner or pilot devices",
    "Ask the vendor to crash its production line so the scanners can be delivered on the original date", "Reduce the number of scanners in the contract so the vendor can deliver the smaller order on time", "Ask operations to move the peak season so that the go-live can follow the new delivery date"],
   "Re-sequencing within the project's control mitigates the delay. Changing contract scope unilaterally is not possible and crashing the vendor's line is outside the PM's control.", "case_02"),
 # case_03
 S("PR.6.6", "predictive", "What are CPI and SPI, and what should the project manager do?",
   ["CPI 0.80, SPI 0.80 — escalate to the steering committee per the governance threshold",
    "CPI 1.25, SPI 1.25 — no action required, because the project is performing better than planned", "CPI 0.80, SPI 1.00 — escalate only the cost issue, because the schedule is still on track",
    "CPI 0.80, SPI 0.80 — keep the variance within the team until the next phase gate review"],
   "CPI = 320/400 = 0.80, SPI = 320/400 = 0.80; both are below 0.9, so the governance threshold requires escalation.", "case_03"),
 S("PR.6.5", "predictive", "Given that the price increase will persist, what is the MOST appropriate EAC?",
   ["1,000,000", "880,000", "800,000", "1,250,000"],
   "Typical variance: EAC = BAC / CPI = 800,000 / 0.8 = 1,000,000. 880,000 would assume the variance is a one-off (AC + BAC − EV).", "case_03"),
 S("PR.9.7", "predictive", "How should the project manager present the status to the steering committee?",
   ["Show current variances, the forecast, root cause and recovery options with a recommendation",
    "Report the overall status as 'amber' and explain the details only if the committee asks for them", "Focus the presentation on achievements so far to maintain the committee's confidence in the team", "Send the complete EVM data set beforehand and let the committee draw its own conclusions"],
   "Status communication should be transparent and decision-oriented. Reporting only a colour hides the information needed to decide.", "case_03"),
 S("BE.1.3", "predictive", "Why does the project have a CPI/SPI escalation threshold?",
   ["It defines when decisions must move to a higher governance level", "It replaces the need to maintain a separate risk register for cost and schedule risks",
    "It allows the project manager to re-baseline the plan alone as long as values stay above it", "It is used at project closure to evaluate whether the project was successful overall"],
   "Governance escalation paths and thresholds define when a decision exceeds the PM's authority. It does not permit the PM to re-baseline alone.", "case_03"),
 # case_04
 S("BE.2.3", "hybrid", "What is the GREATEST compliance threat in the planned training approach?",
   ["Using historic tickets containing personal data without a lawful basis or anonymisation",
    "The large number of agents who will use the assistant without formal certification", "The competitor's similar product, which may set new expectations for the market", "The team's use of two-week sprints instead of a documented predictive plan"],
   "Processing personal data for AI training needs a lawful basis and safeguards (GDPR). The competitor is a market factor, not a compliance threat.", "case_04"),
 S("BE.8.2", "agile", "Marketing wants to accelerate because of the competitor. What should the project manager do?",
   ["Assess the impact on scope and backlog with the product owner and present options including compliance constraints",
    "Accelerate immediately and complete the legal review in parallel after the release", "Continue as planned and ignore the competitor, because the project scope is already agreed", "Stop the project, because the competitor has already captured the market opportunity"],
   "External changes are assessed and prioritised against the backlog. Skipping legal review would trade a market risk for a compliance violation.", "case_04"),
 M("BE.5.1", "hybrid", "Which are valid risks to record in the risk register for this project?",
   ["The assistant may generate inaccurate answers that agents send to customers", "Regulatory requirements for AI systems may change before release"],
   ["The team uses a Kanban board", "The project has a sponsor", "Customer-service agents work in shifts"],
   "Risks are uncertain events affecting objectives (output quality, regulatory change). Facts such as having a sponsor or a Kanban board are not risks.", "case_04"),
 # case_05
 S("P.2.2", "hybrid", "What should the project manager do FIRST about the open disagreement between the two engineers?",
   ["Understand the context and root cause of the disagreement by talking with both engineers",
    "Decide in favour of the architecture proposed by the more senior engineer to save time", "Escalate the disagreement to both former managers so they can align their engineers", "Ask the whole team to vote on the architecture immediately to reach a quick decision"],
   "Analyse the conflict's context before choosing a resolution. Deciding by seniority is forcing and ignores the underlying cause.", "case_05"),
 S("P.3.6", "hybrid", "Team B members are used to detailed instructions and stay silent in planning. Which leadership approach fits BEST?",
   ["Situational leadership: coach team B toward self-organisation while giving more guidance at first",
    "Laissez-faire leadership: let team B figure out self-organisation on its own from day one", "Directive leadership for the whole joint team permanently, to give everyone the same clarity", "Replace team B members with people who already have experience in self-organising teams"],
   "Leadership style is adapted to the team's maturity. Permanent directive leadership would undermine the self-organisation that team A already has.", "case_05"),
 S("BE.7.1", "hybrid", "Employees are worried about job security after the merger. What should the project manager do?",
   ["Assess the cultural and change impact and work with HR and leadership on transparent communication",
    "Treat it as outside the project scope and ask HR to handle any questions from team members", "Reassure the team that no jobs will be lost, to restore motivation and focus quickly", "Ask team members not to discuss the merger during working hours to protect productivity"],
   "Organisational change affects project performance and must be assessed and addressed. Making promises outside the PM's authority destroys trust.", "case_05"),
 # case_06
 S("PR.7.5", "predictive", "How should the project manager handle the subcontractor's cheaper concrete proposal?",
   ["Evaluate it against the carbon and certification requirements and process it as a change request",
    "Accept the proposal, because it reduces cost and the carbon target applies to the whole building", "Reject the proposal immediately, because any change to materials puts the certification at risk", "Let the subcontractor decide, because the structural design is within their contractual responsibility"],
   "Quality requirements include sustainability targets; any change must be evaluated against them. Accepting for cost alone could violate the contract.", "case_06"),
 S("BE.2.5", "predictive", "What is the MOST likely consequence of missing the certification?",
   ["Breach of contract with possible penalties and reputational damage", "A shorter schedule, because certification activities no longer need to be completed", "Higher team morale, because the team no longer has to meet the demanding targets", "No significant consequence, because certification is a voluntary quality label"],
   "Noncompliance with contractual requirements leads to penalties and reputational harm. It does not shorten the schedule or improve morale.", "case_06"),
 S("P.5.1", "predictive", "The facility manager has not been involved. What should the project manager do?",
   ["Identify and engage the facility manager as a key stakeholder to capture operational expectations",
    "Wait until handover to introduce the facility manager to the building and its systems", "Send the final design to the facility manager for information once it is approved", "Ask the client's project lead to represent the facility manager's interests in meetings"],
   "Stakeholders who will operate the result have important expectations; engaging them late causes rework. Information-only sharing is insufficient.", "case_06"),
 # case_07
 S("PR.9.5", "agile", "What does the velocity trend indicate, and what should happen FIRST?",
   ["A consistent decline; explore the causes with the team", "The team is losing focus; increase pressure and commit to more points",
    "Normal variation between sprints; no action is required at this point", "The estimates were wrong; re-estimate all remaining backlog items first"],
   "A steady decline over four sprints is a signal to investigate with the team. Increasing pressure ignores the reported impediments.", "case_07"),
 S("BE.4.3", "agile", "The team keeps waiting for security approvals. What should the project manager do?",
   ["Work with the security department on a faster approval path, e.g., early involvement or agreed standards",
    "Tell the team to proceed without waiting for approvals and obtain them retroactively before release", "Log the impediment in the impediment board and wait for the security department to speed up", "Ask the product owner to formally accept the security risk so the team can continue without approvals"],
   "A servant leader actively removes impediments by collaborating with those involved. Skipping approvals violates compliance.", "case_07"),
 S("BE.6.1", "agile", "Retrospective action items are rarely implemented. What is the BEST improvement?",
   ["Limit to one or two actionable improvements per sprint and add them to the sprint backlog with an owner",
    "Stop holding retrospectives until the team has completed the existing list of action items", "Have the project manager decide on the improvements and assign them to team members", "Document all improvement ideas in the lessons learned register for future projects"],
   "Improvements need to be small, owned and visible in the plan to be implemented. Stopping retrospectives removes the improvement mechanism.", "case_07"),
 S("P.3.3", "agile", "Unclear acceptance criteria keep coming up. Who should primarily resolve this?",
   ["The product owner together with the team during backlog refinement", "The project manager alone, as the person accountable for delivery",
    "The security department, since approvals depend on the criteria", "The sponsor, who owns the business case and the release date"],
   "Acceptance criteria are clarified between product owner and team in refinement. The PM facilitates but does not own product decisions.", "case_07"),
 # case_08
 S("P.4.6", "predictive", "How should the project manager address the head of finance's doubts?",
   ["Meet the head of finance to understand concerns and involve them in addressing them",
    "Escalate the head of finance's resistance to the CEO so the go-live is not endangered", "Refer the head of finance to the passed acceptance tests, which prove the system works", "Exclude the finance department from the go-live and bring it on board in a later wave"],
   "Build trust by understanding and addressing concerns directly. Escalating first damages the relationship.", "case_08"),
 S("BE.7.2", "predictive", "Accountants keep using their old spreadsheets. What does this indicate?",
   ["Adoption risk: change management activities such as training and reinforcement are needed",
    "The new system has failed technically and must be re-tested before go-live", "Nothing significant, because users always adapt to new systems over time", "A need to extend the project scope with additional spreadsheet features"],
   "Parallel use of old tools indicates weak adoption; benefits will not be realised without change management. Tests passed, so technical failure is not indicated.", "case_08"),
 S("PR.10.3", "predictive", "What must be completed before handing over to operations support?",
   ["Confirm transition readiness: documentation, knowledge transfer and support acceptance",
    "Release the project team so that the members can start on their next assignments without delay", "Archive all project files in the document management system", "Close all vendor contracts and settle the final invoices with the suppliers"],
   "Transition readiness includes operational documentation and acceptance. Releasing the team first would lose the knowledge operations needs.", "case_08"),
 S("P.6.3", "predictive", "Which measure BEST shows whether the finance users' expectations are met after go-live?",
   ["User satisfaction and adoption metrics tracked after go-live", "The number of passed test cases in the final acceptance test",
    "The project's final cost performance index (CPI) at closure", "The number of change requests submitted during the project"],
   "Customer satisfaction and adoption measure expectations. Passed tests show technical conformance, not user satisfaction.", "case_08"),
 # case_09
 S("P.7.1", "hybrid", "What should the project manager do FIRST about the knowledge held by the leaving researchers?",
   ["Identify which knowledge is critical and plan how to capture and transfer it before they leave",
    "Ask HR to extend the researchers' contracts until all knowledge has been documented", "Export all chat messages and files of the researchers to a central project archive", "Accept the loss of knowledge, because the project is ending anyway and the budget is needed"],
   "Start by identifying critical knowledge, then choose transfer methods. Exporting chats without structure captures data, not usable knowledge.", "case_09"),
 S("PR.10.4", "predictive", "The sponsor wants a quick close. Which activity must NOT be skipped?",
   ["Resolving the supplier's open invoice dispute and formally closing the contract", "The closing celebration to recognise the team's achievements",
    "Updating the team charter with the final working agreements", "Releasing the remaining budget back to the portfolio immediately"],
   "Procurement closure requires settling claims before formal closure. Leaving disputes open creates legal and financial exposure.", "case_09"),
 S("BE.6.3", "hybrid", "How can the organisation benefit from this project's lessons in future projects?",
   ["Update organisational process assets such as templates and the lessons learned repository",
    "Store the lessons in the project folder so they are available if someone asks for them", "Email a summary of the lessons to the sponsor as part of the final report", "Discuss the lessons informally with the team at the closing event"],
   "Updating OPAs makes lessons reusable across the organisation; a project folder is rarely consulted again.", "case_09"),
 # case_10
 S("BE.8.3", "agile", "What does this situation show about the external business environment?",
   ["It must be reviewed continually because changes can alter scope and backlog priorities",
    "It mainly matters at project initiation, when the business case and scope are defined", "It is the sponsor's responsibility, and the team should focus on delivering the backlog", "It is less relevant for agile projects, because short sprints adapt to change automatically"],
   "The ECO expects continual review of external changes affecting scope/backlog. It is not only an initiation activity.", "case_10"),
 S("PR.3.2", "agile", "How should the new legal features be prioritised in the backlog?",
   ["High priority, because compliance by the effective date is a must-have that protects the product's value",
    "Low priority, after the marketing features, because they do not generate additional revenue", "Only if story points allow after the planned features, since the law takes effect in four months", "In a separate follow-up project after the release, so the current release plan is not disturbed"],
   "Mandatory legal features are must-haves; without them the product cannot be sold. Delaying them risks losing all value.", "case_10"),
 S("BE.3.2", "agile", "Marketing asks why some of its features moved down the backlog. What should the project manager ensure?",
   ["The product owner communicates the reprioritisation and its reasons transparently", "Marketing is excluded from sprint reviews until the legal features have been delivered",
    "The team secretly works on both marketing and legal features to avoid the discussion", "The reprioritisation is not communicated until the next release to avoid conflict"],
   "Changes and their status must be communicated. Hiding reprioritisation erodes trust.", "case_10"),
 S("P.1.4", "agile", "Some team members see the law as a distraction. What should the project manager do?",
   ["Reconnect the team with the product vision and explain how compliance protects customer trust and value",
    "Instruct the team to implement the legal features as a binding management decision that is not open for discussion", "Allow the doubting members to work only on the marketing features", "Escalate the team members' attitude to HR as a performance issue"],
   "Misunderstanding the vision is addressed by clarifying the root cause and linking work to purpose. Ordering compliance does not create alignment.", "case_10"),
 # case_11
 M("PR.8.8", "predictive", "Which schedule compression options are available here?",
   ["Crash prototyping by adding the borrowed senior engineer", "Fast track testing to partly overlap with prototyping"],
   ["Add resources to marketing material", "Remove float from marketing material", "Extend the trade fair date"],
   "Compression applies to critical-path work: crashing (add resources) and fast tracking (overlap). Marketing material has float and does not shorten the project.", "case_11"),
 S("PR.4.2", "predictive", "Before borrowing the senior engineer, what should the project manager do?",
   ["Agree availability with the other project's manager and the resource owner",
    "Assign the engineer to the project directly, because the trade fair has priority", "Ask the engineer to split their time and work overtime on both projects", "Hire an external contractor instead, without analysing the cost and onboarding time"],
   "Shared resources must be negotiated with their owners to avoid conflicts. Assigning directly bypasses resource governance.", "case_11"),
 S("BE.5.2", "predictive", "The test lead warns about rework if testing overlaps prototyping. How should this be handled?",
   ["Analyse the rework risk and include it in the decision on fast tracking", "Ignore the warning, because the trade fair date is fixed and cannot move",
    "Cancel part of the testing to recover time before the trade fair", "Replace the test lead with someone who supports the fast-tracking plan"],
   "Fast tracking increases risk; it should be analysed and weighed. Ignoring it can lead to more delay through rework.", "case_11"),
]
