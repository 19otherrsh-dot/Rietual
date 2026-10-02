# Build Spec — The Failure Layer

**Implements:** PRD v1.1 §4.4 (with dependencies on §4.1.2, §4.3.5, §4.5.4, §4.6.1)
**Phase:** 1 — blocking for launch
**Version:** 1.1
**Date:** 8 August 2026
**Amended by:** DECISIONS-v1 — D1, D2, D4, D5, D11 applied below

> **Why this spec exists.** §4.4 is the differentiator and the spine of the product, and it is almost entirely a *copy and timing* problem rather than an engineering problem. The state machine is a week of work. The copy deck is where it succeeds or fails. Most of this document is therefore about words and thresholds, and §6 is the part to fight about in review.

---

## 1. Scope & definitions

Getting these definitions wrong is the most common way this feature becomes annoying. A "miss" is not the absence of a tap.

| Term | Definition | Detection |
|---|---|---|
| **Scheduled occurrence** | A habit instance the user committed to, in a defined time window | From routine schedule |
| **Completion** | User logged the habit, or an integration inferred it | Explicit tap, HealthKit, or Screen Time signal |
| **Skip** | User proactively declared they're not doing it, before or during the window | Explicit "not today" action |
| **Miss** | Window closed with no completion and no skip | Window close + 2h grace |
| **Planned rest** | Scheduled non-occurrence (rest day, pause clause, transition mode) | Not a miss. Never triggers recovery |
| **Lapse** | 1 miss | State: `lapsed_1` |
| **Extended lapse** | 2–3 consecutive misses | State: `lapsed_2` |
| **Dormancy** | 4+ consecutive misses, or 10 days no interaction with the habit | State: `dormant` |
| **Recovery** | A completion within 72h of a miss | Fires `recovered` event — **the headline metric** (PRD §9.2) |

### 1.1 Skip is a first-class action, not a failure

A user who taps "not today" has done something *good*: they've maintained an accurate model of their own behavior and kept our data clean. Skip must be:

- Available in one tap from the notification itself, without opening the app
- Never penalized in streak accounting when used ≤2×/week
- Optionally annotated with one tap ("no time" / "too tired" / "wasn't the right day" / "forgot until now") — **this annotation is the seed for the coping plan in §4**

The single biggest data-quality lever in the product is making skip easier than ignoring. Most apps make skip *harder* than ignoring, because they're optimizing for a completion-rate number that they are, in effect, choosing to corrupt.

### 1.2 The grace window

No recovery messaging fires until **2 hours after the window closes**, and never between 22:00 and 07:00 local. Someone who does their evening routine at 21:40 instead of 21:00 has not failed at anything, and telling them so at 21:01 is how a product earns its uninstall.

---

## 2. State machine

### 2.1 Per-habit states

```
                    ┌──────────────────────────────────────────┐
                    │                                          │
   new ──▶ forming ─┼──▶ lapsed_1 ──▶ lapsed_2 ──▶ dormant ────┤
             │      │       │             │           │        │
             │      └───────┴─────────────┴───────────┘        │
             │           (completion → forming)                │
             │                                                 │
             ├──▶ established ──▶ graduated                    │
             │    (SRBAI ≥ threshold, 2 consecutive measures)   │
             │                                                 │
             └──▶ retired ◀────────────────────────────────────┘
                  (user-initiated, or 21d dormant)
```

**Transition rules:**

| From | To | Trigger |
|---|---|---|
| `forming` | `lapsed_1` | 1 miss |
| `lapsed_1` | `forming` | Completion within 72h → emits `recovered` |
| `lapsed_1` | `lapsed_2` | 2nd consecutive miss |
| `lapsed_2` | `forming` | Completion → emits `recovered_deep` |
| `lapsed_2` | `dormant` | 4th consecutive miss or 10d no interaction |
| `dormant` | `forming` | Completion, or user re-plans the habit |
| `dormant` | `retired` | 21d in dormant, **with user confirmation** — never silent |
| `forming` | `established` | SRBAI ≥ threshold on 2 consecutive biweekly measures |
| `established` | `graduated` | SRBAI sustained + 30d of ≥80% unprompted completion (§4.3.5) |
| `graduated` | `forming` | Maintenance check shows decay — re-entry is offered, not forced |
| any | `paused` | Transition mode, pause clause, or user pause. **All lapse logic suspended** |

**`paused` is load-bearing.** Every lapse rule above must check for it first. A user in transition mode (§4.4.5) who receives a lapse message has been failed by us, not the other way around.

### 2.3 `lapsed_1` is a state, not an event (D1)

**We do not raise the first miss. We always answer it if the user does.**

| | `lapsed_1` | `lapsed_2`+ |
|---|---|---|
| **Push-initiated** (we surface it) | **Never** | Yes, per §3 |
| **Pull-initiated** (user opens the app) | Light acknowledgment (§4.2) | Full recovery break |

After one miss most people have not registered a failure. Surfacing it *tells them one occurred* — manufacturing the exact event this entire section exists to soften. A user who forgot to stretch on Tuesday needs Wednesday to arrive normally.

`lapsed_1` remains a tracked state because it drives skip-annotation capture (§1.1), coping-plan seeding (§5), and the recovery metric (§11.1). It simply has no push-side trigger.

**A pull is different.** A user who opens the app after a miss has come looking, and leaving them with an unacknowledged gap on the screen is its own small unkindness. They get the light version.

### 2.2 Per-user states (drive coach queue, §8)

| State | Definition | Action |
|---|---|---|
| `engaged` | ≥1 completion in 7d, no crisis signal | None |
| `at_risk` | 2+ habits in `lapsed_2`, or recovery self-efficacy ≤3 | Coach queue, priority 2 |
| `action_crisis` | ACRISS-adapted score above threshold (§5) | **Coach queue, priority 1** |
| `disengaged` | No app interaction 10–21d | Fresh-start-timed re-entry (§4.1.5), not daily nags |
| `churned` | No interaction 21d+ | One transition-mode probe, then stop. See §9.3 |

---

## 3. The recovery break

Fires on entry to `lapsed_2`, or on re-entry from `dormant`. **Not on `lapsed_1` unless the user opens the app themselves (D1, §2.3).** 45 seconds, four steps, always ending in a restated plan.

### 3.1 Delivery rules

- **Never as a push notification.** Recovery content is encountered *in-app*, on next open. A push that says "you missed your habit" is the shame vector this entire feature exists to prevent.
- **First miss is silent on our side (D1).** No badge, no in-app interstitial, no red dot. If the user opens the app of their own accord, §4.2's light acknowledgment appears inline — never as a modal.
- The only push permitted post-miss is a neutral, non-referential re-engagement at the next scheduled occurrence: *"Tomorrow: [habit], [time]."*
- Maximum one recovery break per habit per 72h, and maximum two across all habits per day. A user who missed everything on a bad Tuesday gets one gentle acknowledgment, not six.
- Fully dismissible in one tap, without completing the flow. Dismissal is logged and, if repeated 3×, suppresses recovery breaks for that habit for 14 days.

### 3.2 The four steps

| Step | Function | Duration |
|---|---|---|
| 1. **Name it** | Acknowledge the difficulty. No minimizing, no reframing | ~5s |
| 2. **Common humanity** | Situate it as normal, using real cohort data | ~10s |
| 3. **Smallest next version** | Shrink the ask to something obviously doable | ~20s |
| 4. **Restate the plan** | Re-commit the user's own specific if-then | ~10s |

---

## 4. Copy deck

**Every string below is a draft for qualitative testing (§13.3), not final copy.** Tone is the feature; these are the starting point for that testing, and the tone rules in §6 are what testing should be checked against.

### 4.1 Variant matrix

Copy varies on four axes:

| Axis | Values |
|---|---|
| Depth | `lapsed_1` · `lapsed_2` · `dormant_return` |
| ELM track (§4.1.3) | central · peripheral |
| Obstacle recorded? | yes (quote it back) · no |
| Habit class | add (§4.3) · quit (§4.7) |

Peripheral-track users get steps 1+3 only, compressed to ~15 seconds. Central-track users get all four plus an optional "why this works" expander.

### 4.2 `lapsed_1` — light acknowledgment · **pull-initiated only** (D1)

Appears inline on the habit card, only when the user has opened the app themselves. Never a modal, never a push, never a badge.

**Central track:**

> Yesterday didn't go the way you planned it.
>
> Two-minute version today? *[pre-filled micro-habit, one tap]* · **[Not today]**

**Peripheral track:**

> Missed one. Happens.
>
> *[micro-habit, one tap]* · **[Not today]**

That is the entire interaction. No common-humanity step, no plan restatement, no offer to change anything. One miss does not warrant a conversation, and starting one implies it does.

#### 4.2.1 WOOP-offer branch — `if_then` plans (D5)

Users who took quick setup at onboarding hold a plain if-then plan (`plan_type = if_then`) with no obstacle text. **Their first lapse is the right moment to offer WOOP** — on day one the obstacle question is hypothetical and they guess; after a real miss they know.

Offered once, at first `lapsed_1` pull, below the acknowledgment:

> Want to spend two minutes working out what actually gets in the way? It makes the plan a lot harder to drop.
>
> **[Two minutes]** → Onboarding §3 WOOP flow · **[Not now]**

Declined twice → never offered again. The offer does not repeat at `lapsed_2`; by then the recovery break's step 4 is doing this work.

### 4.3 *(merged into §4.2 — see D1)*

### 4.4 `lapsed_2` · central · add-habit

> **1.** Three days now. I'd guess this one's started to feel heavier than it did when you set it up.
>
> **2.** This is the point most people quietly drop a habit — not from the missing, but from how the missing starts to feel.
>
> **3.** Two options, and neither is failure: **[Small version, for a week]** — shrink it to something easy, and we'll ask about going back on day 7 · **[Pause it]** — park it for a week, no streak damage, no reminders
>
> **4.** Or, if you want to keep it as is: *"[their if-then]"* — tomorrow, same plan.
>
> *[expander: Why we're offering to shrink it →]*

**Shrinking is time-boxed to 7 days (D2).** On day 7 the habit auto-prompts to restore:

> The small version has run a week. Back to the full one, or keep it small a bit longer? · **[Back to full]** · **[Another week]** · **[Make small the new normal]**

A user came for an outcome, not a streak. Permanently shrinking a 30-minute walk to two minutes protects our retention number while quietly abandoning what they wanted — and restoring on schedule is a competence experience rather than a concession. The third option exists because sometimes small genuinely *is* the right size, but it has to be chosen deliberately rather than arrived at by drift.

### 4.5 `dormant_return`

> **1.** Been a while. Welcome back.
>
> **2.** *[no guilt framing, no "we missed you", no summary of what was missed]*
>
> **3.** Rather than pick up where it stopped, want to rebuild this one from scratch? Most things worth restarting are worth re-planning. **[Rebuild]** · **[Resume as it was]** · **[Retire it]**

**Hard rule for `dormant_return`:** never display a lapsed streak count, a "days since" figure, or a completion-rate chart on this screen. The user knows. Showing them is not information, it's a reproach.

### 4.6 Quit-track variants (§4.7)

**Phase 1 scope (D4): digital and behavioral targets only.** Substances, alcohol, and anything adjacent to disordered eating are excluded from the category picker entirely — not permitted with a warning. The copy below was written by analogy from missed walks, and lapse in a clinically loaded category can do real harm. Unblocks with clinical review in Phase 2.

Cessation lapses carry more shame than omission lapses and need shorter, flatter copy.

> **1.** It happened. Noting it is the useful part — that's how the cue gets visible.
>
> **2.** *[skip common-humanity step for quit habits — it reads as permission-giving]*
>
> **3.** What was going on right before? *[one-tap: bored · stressed · tired · with someone · nothing in particular]*
>
> **4.** Your competing response was: *"[their CR]"*. Want to keep it or swap it? · **[Keep]** · **[Swap]**

### 4.7 Strings that must never ship

These are the failure modes, written out so review has something concrete to reject against.

| ❌ Never | Why |
|---|---|
| "You broke your 12-day streak!" | Loss-framed dramatization of exactly the moment AVE fires |
| "Don't give up! You've got this! 💪" | Cheerleading signals we haven't understood what happened; reads as a machine |
| "You've completed 3 of 7 habits this week (43%)" | Unrequested performance summary at the worst possible moment |
| "Most successful users never miss two days in a row." | True-sounding, unsourced, and constructs the user as already-failing |
| "Is everything okay?" | Concern-trolling from software; also implies pathology from one missed walk |
| "Your consistency score dropped to 61." | A number whose only function is to feel bad |
| "You're falling behind your Circle." | Descriptive norm deployed downward — the boomerang effect (§4.8), pointed at someone already lapsed |
| Any 💀😢😞 or broken-flame/wilting-plant imagery | Visual shame; disproportionately harmful for the segments we target |

### 4.8 The common-humanity data rule

Step 2 quotes a real statistic from our own cohort data. It is subject to a hard constraint:

- **If we do not have ≥200 users in the matched cohort, the step is suppressed entirely** and the flow runs as three steps.
- The number is computed from actual cohort completion data, refreshed weekly, and stored with the message for audit.
- No rounding upward, no "most people" when it's 51%, no borrowed statistics from published literature presented as ours.

At launch we will not have this data. **Step 2 ships dark and turns on when the cohort exists.** This is the correct behavior and it should not be negotiated away for launch polish — a fabricated normalizing statistic in the most trust-sensitive moment in the product is the single worst thing we could do to the positioning in §1.

---

## 5. Coping plans (§4.4.2)

### 5.1 The object

Distinct from the action plan. Separate table, separate lifecycle.

```
CopingPlan
  id
  habit_id
  barrier_text          -- user's words, or picker value
  barrier_class         -- time | energy | competing_goal | environment |
                           forgot | motivation | social | other
  response_text         -- "then I will..."
  created_from_miss_id  -- provenance: which actual failure generated this
  created_at
  active                -- superseded plans retained for §11 analysis
  outcome_completions   -- completions where this plan's barrier was present
  outcome_misses
```

`created_from_miss_id` is the point of the whole design: coping plans are generated **from real failures, not hypothetical ones.** A coping plan with a null provenance is a guess, and should be flagged as lower-confidence in the UI.

### 5.2 Generation flow

Triggered from recovery break step 4 ("Change it"), or automatically offered on 2nd occurrence of the same `barrier_class`.

1. **"What actually got in the way?"** — pre-filled with their skip annotation (§1.1) if present. Free text plus picker.
2. **Classify** — user confirms the barrier class.
3. **"If [barrier], then I will ___"** — offer 3 concrete responses drawn from a class-indexed library, plus free text.
4. **Confirm** — the plan is shown in full, once, and stored.

### 5.3 Response library (excerpt)

| Barrier class | Suggested responses |
|---|---|
| `time` | Do the 2-min version · Move it to [most stable alternative cue, from §4.3.3] · Halve it permanently |
| `energy` | Do it seated/lying · Do the first step only and stop · Move to your highest-energy window |
| `competing_goal` | Pick which one wins in advance · Stack it onto the competing activity · Move it off the conflict day |
| `environment` | Pre-place the object the night before · Change the location · Remove the one thing that blocks it |
| `forgot` | Move the anchor to a more stable cue (§4.3.3) · Add a physical cue in the location · Re-enable prompt for 7 days |
| `motivation` | Re-run WOOP for this habit · Bundle it (§4.3.2) · Shrink until it's boringly easy |
| `social` | Tell the specific person in advance · Do it before the social block · Pick a version that works with company |

Note that `forgot` is the only class whose remedy includes re-enabling a prompt, and it's time-boxed — otherwise reminder fading (§4.3.5) unravels through the coping-plan back door.

---

## 6. Tone rules (normative — review checklist)

Every string in the failure layer must pass all seven. This section is the acceptance criteria for copy review.

1. **State the fact, don't characterize it.** "Yesterday didn't go the way you planned" — not "you struggled" or "you slipped."
2. **No second-person judgment, positive or negative.** Neither "you failed" nor "you're doing great." Both are assessments we haven't earned.
3. **The user's own words beat ours.** If we have their obstacle text or their if-then, quote it. It's the highest-signal personalization available and it costs nothing.
4. **Offer a smaller action, never a bigger commitment.** Post-lapse is not the moment to upsell a journey.
5. **Every path out is dignified.** Shrink, pause, and retire must all be presented as legitimate. If retiring a habit is buried or guilt-framed, the whole feature is dishonest.
6. **No numbers unless the number helps them decide something.** Completion percentages, streak counts, and scores are all prohibited in this surface.
7. **Under 40 words per step.** Someone who just failed at a two-minute habit will not read a paragraph about resilience.

**Review process:** copy for this surface requires sign-off from one behavioral advisor and one person from the target segments (§2.1) who has themselves lapsed in testing. Not PM sign-off alone.

---

## 7. Recovery self-efficacy & action crisis

### 7.1 Recovery self-efficacy (§4.4.3)

Single item, per habit:

> *"If you missed this three days in a row, how confident are you that you'd start again?"* — 0 (not at all) to 10 (completely)

- **Cadence:** at habit creation, then every 14 days, then on entry to `lapsed_2`
- **Delivered** as a single tappable scale, never inside a longer survey
- **Thresholds:** ≤3 → coach queue priority 2 + auto-offer shrink · 4–6 → surface coping plan flow · ≥7 → no action

This is cheap, predictive independent of task self-efficacy, and — per PRD §4.4.3 — modeled by no consumer competitor. It is the highest value-per-question item in the battery.

### 7.2 Action crisis (§4.4.4)

**Licensing note, blocking:** Brandstätter's Action Crisis Scale (ACRISS) is a published instrument. **Use the validated wording under appropriate permission** — do not paraphrase it in production. The stems below are a *domain adaptation for prototyping only* and must be replaced before any measurement is used for outcome claims or research (§8.8).

Construct dimensions to capture (6 items, 1–7):
- Conflict between continuing and quitting
- Rumination about disengaging
- Setbacks prompting reconsideration of the goal itself
- Reduced sense that the goal is worth its cost
- Diminished implementation of goal-relevant behavior
- Perceived pressure to abandon

**Cadence:** every 21 days per active journey, plus on entry to `lapsed_2`.
**Threshold:** score above the scale's established cut → user state `action_crisis` → coach priority 1.

**Why this over the LSTM (PRD §8.1):** it ships in Phase 1, it's interpretable, it fires *before* behavior changes, and it gives the coach something to actually say. The model must beat this baseline to justify itself.

---

## 8. Coach escalation (§4.5.4)

Queue is prioritized by signal, never round-robin.

| Priority | Trigger | Coach SLA | Opening context given to coach |
|---|---|---|---|
| 1 | `action_crisis` | 24h | Journey, ACRISS dimensions elevated, obstacle text |
| 2 | Recovery self-efficacy ≤3, or 2+ habits `lapsed_2` | 48h | Habit list, states, coping plan history |
| 3 | `dormant` on a habit the user rated important at intake | 72h | Habit, last completion, original WOOP |
| 4 | Routine weekly check-in | 7d | Standard summary |

**Privacy boundary (§4.5.4):** coaches see habit states, obstacle text, coping plans, and completion patterns. Coaches **do not see** journal entries, mood free-text, or any clinical-instrument responses (none exist in Phase 1 per D12; the boundary is written now so it is already in place if they return in Phase 2). This boundary is disclosed at Guided-tier signup, in the signup flow, not the privacy policy.

**Escalation out:** any coach encountering disclosure of self-harm, abuse, or acute crisis follows the §11 clinical protocol and does not attempt to handle it. This requires the crisis protocol to exist before the Guided tier ships — which makes it a Phase 2 dependency, tracked as such.

---

## 9. Edge & harm cases

### 9.1 The bad week
5+ misses across habits in 48h. **Suppress all individual recovery breaks.** Offer one whole-account message:

> This week's gotten away from you. Want to pause everything for a few days, or shrink it all to the two-minute versions?
>
> **[Pause everything]** · **[Shrink everything]** · **[Leave it]**

This is the highest-value single screen in the spec. It's the moment users delete the app, and every competitor responds to it with six separate notifications.

### 9.2 Illness, bereavement, crisis
User-declarable, one tap, from the pause menu. Pauses all accounting indefinitely with no end-date pressure and no re-engagement pushes. Return is user-initiated only.

### 9.3 Churn probing limits
A `churned` user gets **one** message, timed to the next temporal landmark (§4.1.5), framed as a fresh start rather than a return. If unanswered, no further re-engagement for 90 days. We do not win this user back by volume, and the attempt costs us the option of ever winning them back.

### 9.4 Users for whom lapse is clinically loaded
Disordered-eating, addiction-recovery, and self-harm histories make lapse messaging genuinely risky. Until §11's clinical review exists, we do not ship condition-specific programs (§8.10) — and the generic copy is written to be safe by default, which is much of why §6 rule 2 forbids assessment language in either direction.

### 9.5 Reduced-motion & screen reader
The recovery break has no animation dependency; it must read correctly as a linear document. Verify the four steps announce in order and the dismiss control is reachable first, not last.

---

## 10. Data model additions

```
Miss
  id, habit_id, scheduled_occurrence_id, detected_at
  window_start, window_end
  skip_annotation           -- from §1.1, nullable
  recovery_break_shown      -- bool
  recovery_break_dismissed  -- bool
  recovered_at              -- nullable; drives §11 headline metric
  depth                     -- lapsed_1 | lapsed_2 | dormant

HabitState
  habit_id, state, entered_at, previous_state
  paused_reason             -- transition | user | illness | pause_clause

RecoverySelfEfficacy
  habit_id, score, measured_at, trigger  -- creation | periodic | lapsed_2

ActionCrisisMeasure
  journey_id, score, subscale_scores, measured_at, instrument_version
```

`instrument_version` on the ACRISS measure is required for §8.8 — research claims need to know which wording produced which number.

---

## 11. Measurement & experiment design

### 11.1 Headline metric

**Lapse recovery rate** = completions within 72h of a miss ÷ total misses.

Segmented by: depth · ELM track · obstacle-recorded · habit class · coach tier · whether a coping plan existed.

Per PRD §9.2: *if this doesn't move, §4.4 is theater.* Baseline it in the first 60 days with the recovery break disabled for a holdout.

### 11.2 First micro-randomized trial (§8.8)

| Element | Value |
|---|---|
| **Decision point** | Entry to `lapsed_2` + 2h — **not `lapsed_1`** (D1) |
| **Randomized** | Recovery break variant: full (4-step) · minimal (step 3 only) · none |
| **Tailoring variables** | ELM track, plan type (`woop` \| `if_then`), obstacle-recorded, time of day, recent miss density |
| **Receptivity** | Excluded if `paused`, in a bad week (§9.1), or 2+ recovery breaks already today |
| **Proximal outcome** | Completion of that habit within 72h |
| **Distal outcome** | Habit still active at day 30; SRBAI at day 28 |

**Powering note:** misses are frequent, so this trial powers unusually fast — likely within 6–8 weeks of reaching a few thousand active habits. That makes it the right first MRT and a good forcing function for building the §8.8 infrastructure early rather than in Phase 3.

### 11.3 Secondary questions

1. Does quoting the user's own obstacle text outperform generic step 4? (Cheap, high-prior, run it second.)
2. Does the shrink offer at `lapsed_2` increase 30-day survival, or does it reduce the habit to something that no longer delivers the outcome?
3. Does the §9.1 bad-week screen reduce 7-day churn? Hard to power — rare event — but it's the highest-stakes screen we have.
4. Does the §4.2.1 WOOP offer at first lapse convert, and do converted plans outperform? (D5 predicts yes on both; it is the cheapest of these to run.)

*The cue-stability arm proposed in v1.0 of this spec is **removed** (D11). Stability feedback now ships at habit creation only and is prohibited in the recovery break, so there is nothing here to randomize.*

---

## 12. Acceptance criteria

Launch-blocking:

- [ ] Skip is available in one tap from the notification, without opening the app
- [ ] No recovery messaging fires within the grace window or 22:00–07:00 local
- [ ] `paused` suppresses all lapse logic, verified against transition mode, pause clauses, and user pause
- [ ] No recovery content is ever delivered by push
- [ ] **First miss produces nothing user-visible unless the user opens the app** — no push, no badge, no red dot, no modal (D1)
- [ ] Shrink auto-prompts to restore on day 7 (D2)
- [ ] Quit Track category picker excludes substances, alcohol, and eating-related targets (D4)
- [ ] Cue-stability feedback appears nowhere in the recovery break (D11)
- [ ] Step 2 is suppressed when cohort n < 200 — verified with a real empty-cohort test, not a code review
- [ ] No string in the surface displays a streak count, completion percentage, or score
- [ ] Every recovery break has a one-tap dismiss reachable before any other control
- [ ] Retire, pause, and shrink are equally prominent at `lapsed_2`
- [ ] §9.1 bad-week suppression fires correctly at 5+ misses/48h
- [ ] All copy passes the seven §6 rules, signed off by an advisor and a segment participant
- [ ] Screen reader reads the four steps in order; reduced-motion has no degradation
- [ ] Holdout cohort configured before launch so §11.1 has a baseline

Deferred to Phase 2 (with dependencies tracked):

- [ ] Coach escalation queue — depends on Guided tier + crisis protocol
- [ ] ACRISS under license — depends on permissions
- [ ] MRT infrastructure — depends on §8.8

---

## 13. Open questions — resolved

All four are closed in DECISIONS-v1.

| v1.0 question | Resolution |
|---|---|
| 1. Is 72h the right recovery window? | **Closed — D3.** Kept, but as a *metric definition only*. Nothing the user experiences depends on it now that intervention timing is governed by D1, so it needs to be defensible rather than optimal. It spans a weekend, which is the shape of most real lapses |
| 2. Does shrinking cannibalize the habit? | **Closed — D2.** Time-boxed to 7 days with an auto-restore prompt. The user gets persistence through a bad week without silently losing the outcome they came for |
| 3. Should `lapsed_1` fire a recovery break? | **Closed — D1. No.** One miss gets silence on our side, and a light acknowledgment if the user comes looking. See §2.3 |
| 4. Quit-track lapse copy | **Closed — D4.** Scope narrowed to digital/behavioral targets for Phase 1; clinically loaded categories excluded from the picker pending review |

**Nothing in this spec is now blocked on a decision.** The one thing still genuinely unknown — whether the recovery protocol moves lapse recovery rate (PRD §12.1) — is a result to wait for, not a call to take, and the holdout in §11.1 answers it by month three.
