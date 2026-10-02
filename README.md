# RITUAL

A behavioral-science habit and wellness platform. Direct challenger to Fabulous (30M+ downloads, Google's Best App for Self-Care).

**Status:** Phase 1 specified end to end. Backend boots and serves — **165 tests passing**, 10 tables, 9 API endpoints ([backend/](backend/README.md)). Critical path remains clinician contracting and legal review, neither of which is an engineering task (see [PLAN-phase1-v1.md §1](PLAN-phase1-v1.md)).

---

## The thesis

> **We are built around failure, not success.**

Every competitor optimizes the completed-habit path. Lapse is the modal user experience and the primary retention failure point, and it is where this product lives.

### Three differentiators

| | What it means | Where |
|---|---|---|
| **The Failure Layer** | 45-second recovery break, coping plans generated from real failures, self-compassion framing rather than encouragement. **Free forever, including after cancellation.** | [PRD §4.4](PRD-RITUAL-v1.1.md) · [SPEC-failure-layer](SPEC-failure-layer-v1.md) |
| **Habits graduate** | SRBAI-gated automaticity → prompts fade on a schedule → the habit leaves the tracker. The only app with an incentive to make itself less necessary. | [PRD §4.6.4](PRD-RITUAL-v1.1.md) · [SPEC-habit-engine §9](SPEC-habit-engine-v1.md) |
| **Validated instruments** | SRBAI, BREQ-3, MCTQ, WHO-5, PSS-10 — real instruments, evidence-graded, not invented scales. | [PRD §4.6.1, §5.1](PRD-RITUAL-v1.1.md) |

---

## Document map

Read in this order.

| # | File | ~Lines | What it is |
|---|---|---|---|
| 1 | **[PRD-RITUAL-v1.1.md](PRD-RITUAL-v1.1.md)** | 511 | The authoritative spec. Features, behavioral science foundations with evidence grades, monetization, roadmap, risk. **Currently at v1.2** — the filename is historical |
| 2 | **[DECISIONS-v1.md](DECISIONS-v1.md)** | 143 | 19 closed decisions (D1–D19), each with its user-need rationale. **Already applied into the documents below** — see precedence note |
| 3 | **[PLAN-phase1-v1.md](PLAN-phase1-v1.md)** | 186 | 12 sprints, 5 milestones, consolidated launch gates, go/no-go points |
| 4 | **[SPEC-onboarding-v1.md](SPEC-onboarding-v1.md)** | 311 | Onboarding flow, WOOP implementation, instrument staging, paywall placement |
| 5 | **[SPEC-habit-engine-v1.md](SPEC-habit-engine-v1.md)** | 216 | Anchors, cue-stability scoring, scheduling, reminder fading, probe days, graduation |
| 6 | **[SPEC-journeys-v1.md](SPEC-journeys-v1.md)** | 228 | Journey architecture, Sleep Reset in full with its safety gate, five journey outlines |
| 7 | **[SPEC-failure-layer-v1.md](SPEC-failure-layer-v1.md)** | 343 | State machine, copy deck, tone rules, coping plans, MRT design |
| 8 | **[STACK-open-source-v1.md](STACK-open-source-v1.md)** | 225 | Swift/Kotlin native, Python/FastAPI, Postgres, Valkey. No third-party SDKs in the client. License traps register |
| 9 | **[SPEC-crisis-protocol-v1.md](SPEC-crisis-protocol-v1.md)** | 250 | Phase 2. Always-available help, coach response script, emergency-services position, data handling. **Draft pending clinical and legal sign-off** |

**Precedence.** DECISIONS-v1 has been applied into the PRD and specs — they are current, not stale. Amended passages carry inline `(Dn)` markers, and each document's header names the decisions applied to it. Where a document and DECISIONS-v1 appear to disagree, that is a bug; report it.

### Code

| Path | What |
|---|---|
| **[backend/ritual/](backend/README.md)** | Domain core. Framework-free, stdlib only — scheduling with DST/travel correctness, cue-stability circular statistics, fade ladder with probe days, unprompted attribution, lapse state machine, sleep titration. **105 tests** mapped to the PLAN §7 launch gates |
| **[backend/src/](backend/README.md)** | Application layer — FastAPI routers, SQLAlchemy models, Alembic, Kratos, Celery workers, APNs/FCM, the five instruments. Imports `ritual`; never the reverse |

### The four documents an engineer needs

4, 5, 6, 7 — plus 8 for the stack. The PRD is context; the specs are what you build from.

---

## Phase 1 scope (months 1–6)

**Ships:**
- Full Failure Layer — recovery breaks, coping plans, recovery self-efficacy, action-crisis scale
- WOOP onboarding with the quick-setup fork
- Cue-stability audit **at habit creation** (never after a failure — D11)
- Reminder fading, with **unprompted completion as the primary success metric**
- Habit graduation
- Six journeys, three of them clinician-gated
- Instruments: WHO-5, MCTQ, SRBAI, BREQ-3, PSS-10

**Deliberately excluded:**
- PHQ-8 / GAD-7 (D12) — no clinical screening we cannot act on
- Guided tier and human coaches (D14) — gated on the crisis protocol
- Circles, biometrics, AI coaching, temptation bundling, transition mode — [PLAN §8](PLAN-phase1-v1.md)

**Commercial:** paywall at day 7, flat (D7). Failure Layer free forever (D8).

---

## Three decisions that cost money on purpose

Recorded here so a later pricing review has to reverse them explicitly rather than let them erode.

1. **D7 — day-7 flat paywall.** Not gated on completions, because completion-gating charges the people it is working for and lets the strugglers drift away.
2. **D8 — Failure Layer free forever**, including after cancellation. Our most expensive feature is our free one. A user who cancels is often a user who is struggling; withdrawing lapse support at that moment would be the most cynical thing in the product.
3. **D13 — coach caseload capped at 150:1**, by whether a coach can remember you, not by margin. May force a higher price or a waitlist. Both beat launching the tier hollow.

Full reasoning in [DECISIONS-v1 §G](DECISIONS-v1.md).

---

## What "done" means for Phase 1

A user can install, set up one habit in under four minutes, be reminded until they don't need reminding, miss a day without being punished for it, miss three and be met well, complete a journey that leaves habits behind, and graduate a habit into their life while we stop talking about it.

---

## Open items

| Item | Status |
|---|---|
| Does the recovery protocol move lapse recovery rate? | Empirical, not a decision. Holdout must be live before launch — [PLAN §6](PLAN-phase1-v1.md) |
| Unhook clinical categories | Blocked on clinical review (D4) |
| Crisis protocol | Drafted — [SPEC-crisis-protocol-v1.md](SPEC-crisis-protocol-v1.md). **Requires clinician and counsel sign-off before any part ships.** One open question is for week 0: whether always-available help (§3) should ship in Phase 1 |
| Coach pilot operating manual | Phase 2, unwritten |
| Journey lesson copy | Blocked on clinician contracting — the Phase 1 critical path |
