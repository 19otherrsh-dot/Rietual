# Phase 1 Build Plan

**Covers:** PRD §10 Phase 1 (months 1–6)
**Sources:** SPEC-onboarding · SPEC-habit-engine · SPEC-journeys · SPEC-failure-layer · STACK-open-source · DECISIONS-v1
**Version:** 1.0
**Date:** 8 August 2026

---

## 1. The critical path is not engineering

The instinct with five specs in hand is to start building. The three longest-lead items in Phase 1 have no code dependency at all, and every one of them can block launch on the last day if started late:

| Item | Lead time | Blocks | Start |
|---|---|---|---|
| **Clinician contracting** — sleep, clinical psych, HRT | 6–10 weeks to contract, then review cycles | 3 of 6 journeys (SPEC-journeys §8) | **Week 0** |
| **Legal review** — FTC HBNR, WA MHMD, AGPL class opinion | 4–8 weeks | Launch, full stop | **Week 0** |
| **Failure-layer copy review** — advisor + a segment participant who has actually lapsed in testing | Needs a testable build first, then 3–4 weeks | The differentiator (SPEC-failure-layer §6) | **Week 8** |

**Week 0 actions, before a line of product code:** contract three clinicians, brief counsel, and recruit the qualitative testing panel. Everything else in this plan can absorb a two-week slip. These cannot.

---

## 2. Dependency graph

```
        ┌──────────────────────────────────────────────────┐
        │ W0: clinicians · counsel · panel recruiting      │  (parallel, no deps)
        └──────────────────────────────────────────────────┘

  Infra ──▶ Engine core ──▶ Prompting ──▶ Fade + probes ──▶ Graduation
   │          (occurrences,    (APNs/FCM)      │                │
   │           anchors,                        │                │
   │           scheduling)                     │                │
   │              │                            │                │
   │              ├──▶ Onboarding ──▶ Instruments               │
   │              │     (plan object)                           │
   │              │                                             │
   │              ├──▶ Miss detection ──▶ Failure layer ────────┤
   │              │                        (copy-blocked)       │
   │              │                                             │
   │              └──▶ Journey API ──▶ Journeys ────────────────┤
   │                                    (clinician-blocked)     │
   │                                                            ▼
   └──▶ Analytics/events ──▶ Holdout config ──▶ MEASUREMENT READY
                                    │
                                    └── must exist BEFORE launch (§6)
```

**Two blockers are external, not technical.** Journeys wait on clinicians; the failure layer's copy waits on review. Both have engineering that can proceed against draft content — build the machinery, swap the words.

---

## 3. Architecture implications of the decisions

Three decisions in DECISIONS-v1 constrain the architecture in ways that are painful to retrofit. Get them right in sprint 1.

### 3.1 D8 — the failure layer is free forever, including post-cancellation

**Entitlement checks must not wrap the failure layer.** The natural implementation — a single `has_premium` gate around feature access — silently breaks this, and breaks it for exactly the user who just cancelled and is struggling.

Required: entitlements are per-feature, and recovery breaks, coping plans, skip, and pause are marked `always_available`. Add a test that runs the full lapse-and-recovery flow **as an expired subscriber**.

### 3.2 D7 — day-7 flat paywall

No usage-coupled trial state machine. The paywall is a function of `account_created_at` and nothing else. This is simpler than what most teams build, and the simplicity is the point — it means we can state the terms plainly at signup.

### 3.3 D12 — no clinical instruments in the Phase 1 build

Not feature-flagged off. **Absent.** No PHQ/GAD tables, no scoring code, no dormant screens. A flag that could be flipped is a flag that gets flipped, and the acceptance criterion (SPEC-onboarding §11) says "do not exist in the build."

---

## 4. Workstreams

| Stream | Owns | Rough shape |
|---|---|---|
| **Platform** | Postgres, FastAPI, Valkey, Celery, occurrences, sync, APNs/FCM, entitlements | 2 engineers |
| **Client** | iOS + Android, offline store, all surfaces | 2–3 engineers |
| **Content** | Journey lessons, reflection prompts, all copy | 1 writer + 3 contract clinicians + advisor |
| **Measurement** | Events, holdout, instrument scoring, MRT scaffolding | 1 engineer, part-time from sprint 6 |
| **Design/PM** | Flows, copy review process, qualitative panel | 1–2 |
| **Legal/compliance** | §6.2 review, SDK audit, AGPL opinion | external + PM |

---

## 5. Sprint sequence (12 × 2 weeks)

### M0 · Foundations — sprints 1–2

- Infra: Postgres, FastAPI skeleton, Valkey, Celery, Forgejo + CI, OpenTofu
- Auth (Ory Kratos), **per-feature entitlements** (§3.1)
- Event pipeline: first-party collection to our own endpoint, no SDKs
- Client skeletons, offline SQLite (GRDB / Room), event-sourced sync
- **Parallel, non-engineering:** clinician contracts signed, counsel briefed, panel recruited

**Exit:** a user can sign up, the client syncs offline writes, entitlements are per-feature and tested against an expired-subscriber case.

### M1 · Engine core — sprints 3–4

- `Habit`, `Anchor`, `Occurrence` (SPEC-habit-engine §1)
- Occurrence materialization, 7 days ahead, **local wall clock** (§4.2)
- DST + timezone-change test suite — both transition directions, plus a simulated flight
- Windows, grace, skip as a first-class one-tap action
- Anchor class priors; calendar-derived candidate ranking

**Exit:** habits schedule correctly through DST and a timezone change. Skip works from the notification without opening the app.

### M2 · Onboarding — sprints 5–6

- Screens 1–13 including the D5 fork
- WOOP with non-skippable 15s timers; quick-setup path; `plan_type`
- Internal/external drill-down, user-performed, no model
- ELM screener, chronotype quick-2, self-efficacy, WHO-5 at S2
- Congruence check; anchor picker with stability basis shown
- Notification permission at screen 13, naming the anchor time

**Exit:** time-to-value-moment under 4 min (proper) / 3 min (quick) at p50 **on real devices, not simulator**. Obstacle text verified stored verbatim and unbounded.

### M3 · Prompting, fading, miss detection — sprints 7–8

- APNs direct + FCM HTTP v1 as transport, no vendor SDK
- Fade ladder L0–L4, advancement and one-level regression
- **Probe days** with all five §5.3 fences
- Unprompted attribution on **delivery** time, including delayed-delivery case
- Miss detection: window close + 2h, never 22:00–07:00, `paused` checked first
- Bad-week suppression (5+ misses / 48h)

**Exit:** unprompted-completion rate computes correctly across fade levels; probe misses provably excluded from lapse progression.

### M4 · Failure layer — sprints 9–10

- State machine incl. §2.3 pull/push distinction — **first miss produces nothing user-visible unless pulled**
- Recovery break, all variants, in-app only, never push
- Coping plans with `created_from_miss_id` provenance
- Recovery self-efficacy; action-crisis scale (adapted stems pending licence)
- Shrink time-boxed to 7 days with restore prompt
- Step 2 **ships dark** (cohort n < 200)
- **Copy review completes here** — advisor + segment participant

**Exit:** every string passes the seven §6 tone rules with recorded sign-off. No streak count, percentage, or score anywhere in the surface.

### M5 · Journeys + graduation — sprints 11–12

- Journey API (≤1 habit/day, ≤5 per journey), completion-based advancement
- Six journeys; **Sleep Reset gate unskippable via every entry point including deep links**
- Sleep window algorithm with the 5.5h floor, unit-tested adversarially
- Sleepiness override on days 5/10/15
- SRBAI scheduling; graduation criteria; the graduation moment
- Goal-conflict detection

**Exit:** clinical sign-offs recorded for all three gated journeys. Graduation stops prompts permanently and is celebrated properly.

### Hardening — runs inside sprints 10–12

- Accessibility: screen reader on WOOP timers and the recovery break; reduced-motion
- **Third-party SDK egress audit — launch blocker** (STACK §6.2)
- Data export/delete, end to end
- Holdout cohort configured and verified emitting (§6)
- Load and offline-reconciliation testing

---

## 6. The measurement gate

**Launch is blocked until the holdout is live and verified.**

The headline metric is lapse recovery rate (SPEC-failure-layer §11.1), and it is meaningless without a baseline. A holdout configured after launch produces a comparison against a period when the product was different in a dozen other ways.

Required before day one:
- Holdout cohort receiving no recovery break, sized to detect a meaningful difference within 60 days
- Every decision point logged **including non-intervention ones** (STACK §6.1) — the standard way an MRT is ruined before analysis
- `plan_type` recorded so `if_then` plans are never counted as mental contrasting
- Onboarding funnel instrumented per screen, with 7a–7d individually

This is roughly a week of work and it is the easiest thing in the plan to defer into never.

---

## 7. Consolidated launch gates

Drawn from all five specs. Not all acceptance criteria — the ones that would be expensive or harmful to discover late.

**Correctness**
- [ ] Wall-clock scheduling verified across both DST directions and a timezone change
- [ ] Circular statistics for temporal stability; midnight-spanning unit test
- [ ] Sleep window algorithm cannot propose < 5.5 hours, under adversarial diary data
- [ ] Unprompted attribution uses delivery time
- [ ] `paused` suppresses all lapse logic

**Harm prevention**
- [ ] First miss produces nothing user-visible unless the user opens the app
- [ ] No recovery content by push, ever
- [ ] Sleep Reset gate unreachable-around via every entry point
- [ ] Sleepiness check overrides titration
- [ ] Unhook picker excludes substances, alcohol, eating targets
- [ ] Probe misses excluded from lapse progression and streak loss
- [ ] No PHQ/GAD code, tables, or screens exist in the build

**Honesty**
- [ ] Common-humanity step suppressed at cohort n < 200, verified with a real empty-cohort test
- [ ] No unsourced precise numbers in any lesson or tip
- [ ] Stability basis (prior/calendar/observed) always shown
- [ ] `if_then` plans never counted as WOOP in metrics or research
- [ ] Every efficacy claim graded against PRD §5.1, advisor-signed

**Commercial / legal**
- [ ] Failure layer works for an expired subscriber (D8)
- [ ] No paywall before day 7 (D7)
- [ ] Cancellation as easy as signup, every jurisdiction
- [ ] Third-party SDK egress audit clean
- [ ] Counsel sign-off on FTC HBNR + WA MHMD posture

**Accessibility**
- [ ] Screen reader: WOOP timers don't steal focus; recovery break reads linearly, dismiss reachable first
- [ ] Reduced motion throughout; timers are numeric, not animated rings

---

## 8. Explicitly not in Phase 1

Named so that scope creep has to argue rather than drift:

Guided tier and coaches · crisis protocol · PHQ-8/GAD-7 · Circles, body doubling, any social · commitment contracts · biometric/wearable integration · temptation bundling with Screen Time · AI coaching and JITAIs · MRT infrastructure beyond event logging · transition mode · marketplace · enterprise · AR · family · clinical integration · Unhook's clinical categories · voice onboarding.

Two are worth noting as *deliberate* rather than merely deferred:

- **Transition mode** (PRD §4.4.5) is a strong retention feature that is cheap to build, and it is still out — it needs life-transition detection that we cannot validate with no users.
- **Temptation bundling** is popular and evidence-supported, and it is out because its effect decayed in the source study and it would consume a Screen Time integration's worth of effort for an accelerant rather than a core mechanic.

---

## 9. Risks to this plan

| Risk | Signal | Response |
|---|---|---|
| **Clinician contracting slips** | No signed contract by week 4 | Ship 3 journeys, not 6. Deep Work, Energy, Confidence need no clinical sign-off. **This is the pre-agreed fallback — decide it now, not in month 5** |
| Copy review finds the recovery break lands wrong | Panel testing in M4 | Budget a full sprint for a rewrite. The machinery is fine; the words are the feature |
| Native parity doubles client cost | Sprint 6 velocity | Ship iOS first, Android 6–8 weeks later. Preferable to shipping both badly |
| Probe days harm users | Probe-miss rate correlates with churn | Drop probe rate to biweekly, accept a noisier metric (engine §12.2) |
| Holdout deferred | It is week 11 and it isn't configured | Hard gate in §6. It is a week of work |
| Sleep Reset is 28 days and clinician says 6 weeks | Review feedback | Ship 6 weeks. Adherence was our reason, efficacy is theirs, and theirs wins (journeys §10.1) |

---

## 10. Go / no-go decision points

| When | Decision |
|---|---|
| **Week 4** | Clinicians contracted? If not → 3-journey launch, decided here |
| **End M2** | Time-to-value under 4 min on real devices? If not, cut instruments before cutting WOOP |
| **End M4** | Does the recovery break pass panel testing? If not, hold launch — this is the product |
| **Week 20** | Holdout live? Non-negotiable gate |
| **Week 22** | SDK audit clean + counsel sign-off? Non-negotiable gate |

---

## 11. What "done" means for Phase 1

A user can install, set up one habit in under four minutes, be reminded until they don't need reminding, miss a day without being punished for it, miss three and be met well, complete a journey that leaves habits behind, and graduate a habit into their life while we stop talking about it.

Everything else in the PRD is Phase 2.
