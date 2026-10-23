# XLRTE Mastery · pass exams, keep the knowledge

[Deutsch](README.md) · Part of [ylsop](https://github.com/ylsop): *why slop?* Tools for people who would rather do it well than do a lot.

**XLRTE Mastery is a local learning cockpit for any exam.** It measures what you actually master instead of ticking off
what you read: every answer is evidence, reviews come when you would otherwise forget, and the forecast tells you
honestly how close you are to the pass mark.

> Knowledge belongs to everyone. Learning today has to be faster than ever, often next to a job, a family or a job
> search. Mastery takes the admin off your hands so your time goes into understanding.

## What's inside

- **Any exam:** pick a learning pack or create your own exam in the setup dialogue (categories, weights, number of
  questions, time, pass mark). See [PACKS.md](PACKS.md).
- **New drills every day, no AI needed:** Mastery generates new questions from your pack's term cards every day, weakest
  objectives first. Deterministic: the same day gives the same set, the next day a new one. The PMP pack adds calculation
  drills (earned value, PERT) with new numbers.
- **Honest measurement:** mastery per objective from your answers, with a half-life. "Guessed and right" counts half,
  "sure and wrong" is reviewed first.
- **Daily recap:** in the evening Mastery benchmarks your day against your learning period: retrievals, accuracy, study
  time and mistakes against the average, the last 7 days and your best day.
- **AI as a tutor, not an oracle:** a learning prompt for Gemini Notebook, NotebookLM or your AI that works from your
  real progress. German and English.
- **German and English:** switch the interface bottom left; setup in both languages.

## Learning packs

| Pack | Language | Content |
|---|---|---|
| PMP (ECO 2026) | EN | 500+ original questions incl. two mock exams, 11 case studies, 200+ term cards, trap radar |
| ITIL 5 Foundation – pattern | DE | 200+ original questions incl. two shadow exams; a model for exams with a published syllabus |
| Scrum basics – sample | DE | a small pack that shows the format |
| Your own exam | any | skeleton from the setup dialogue, filled with your own wording |

## Up and running in five minutes

Requires Python 3.9 or newer.

```bash
git clone https://github.com/ylsop/xlrte-mastery.git
cd xlrte-mastery
./mastery                  # Windows: mastery.cmd
```

The **setup dialogue** opens on first start (local, 127.0.0.1): pack or own exam, date, rhythm, AI connection. Then open
`XLRTE_Cockpit.html`. Start every study day with `./mastery`.

## Privacy: governance by design

Everything runs locally. No account, no telemetry. You choose your AI (subscription, own key, EU provider or local
model); "local only" blocks every remote provider. Details: [PRIVACY.md](PRIVACY.md).

## Content and trademarks

All questions are **original wording**, not exam questions and not text from books or course material. They may contain
mistakes: report them as an issue labelled `content`. PMI, PMP and PMBOK are registered marks of the Project Management
Institute, Inc.; ITIL is a registered mark of PeopleCert. XLRTE Mastery is not affiliated with these organisations.

## Contribute and pilot

Most helpful: reviewing questions, new packs, translations. [CONTRIBUTING.md](CONTRIBUTING.md) · pilot:
[docs/PILOT.en.md](docs/PILOT.en.md) · questions and ideas: GitHub Discussions.

## Licence

Code: [MIT](LICENSE). Learning content: [CC BY-SA 4.0](CONTENT_LICENSE.md). XLRTE Mastery is a project by **XLRTE**
(Prasanna Easwarananthan), born out of his own exam preparation.
