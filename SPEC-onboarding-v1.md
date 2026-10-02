# Build Spec — Onboarding & First Plan

**Implements:** PRD v1.1 §4.1 (with dependencies on §4.2.2, §4.3.3, §4.6.1, §4.9)
**Phase:** 1 — blocking for launch
**Version:** 1.1
**Date:** 8 August 2026
**Amended by:** DECISIONS-v1 — D5, D6, D7, D9, D12 applied below

---

## 1. The problem this spec has to solve first

PRD §4.1 as written specifies an intake that would kill the product.

Counting the items it asks for before the user has done anything:

| Component | Items |
|---|---|
| Lifestyle assessment (§4.1.1) | 5–7 |
| MCTQ short (chronotype) | 6–8 |
| BREQ-3 subset (motivation quality) | ~8 |
| WHO-5 (wellbeing baseline) | 5 |
| ELM screener (§4.1.3) | 3 |
| WOOP (§4.1.2) | 4 steps, free text |
| Self-efficacy calibration (§4.1.4) | 1 |
| **Total** | **~32 items + a writing exercise** |

That is a 10–14 minute intake in front of a user who downloaded a habit app eleven seconds ago. Onboarding abandonment in this category is severe past roughly two minutes, and the users we'd lose first are precisely the segments §2.1 says we're for — the overwhelmed and the executive-function-challenged.

**The instruments are right. The sequencing was wrong.** This spec stages them.

### 1.1 Staging principle

> Only what is needed to personalize the *first* habit goes before the first value moment. Everything else earns its place later, by being asked at a point where the user can see why we're asking.

| Stage | When | Contents | Budget |
|---|---|---|---|
| **S0 — Intake** | First session | ELM screener, 4 lifestyle items, 2 chronotype items, journey pick | ~90s |
| **S1 — First plan** | First session | WOOP, micro-habit definition, self-efficacy, schedule | ~120s |
| **S2 — Baseline** | End of first session, after the plan exists | WHO-5 | ~40s |
| **S3 — Deepening** | Day 7 | Full MCTQ | ~60s |
| **S4 — Motivation quality** | Day 14 | BREQ-3 subset | ~90s |
| ~~S5 — Optional clinical~~ | **Cut from Phase 1 (D12)** | ~~PHQ-8, GAD-7~~ | — |

**Total before first value moment: ~3.5 minutes.** Down from ~12.

### 1.2 The one real conflict: WHO-5 baseline timing

A baseline must be collected before meaningful intervention or we cannot claim change from baseline — which would compromise every outcome claim in PRD §9.2 and the research platform in §8.8.

Moving WHO-5 to day 3 would put it after the user has begun changing behavior. **Resolution: WHO-5 stays in session 1, but at the very end (S2) — after the plan exists and the value moment has landed, before any habit has actually been performed.** This is still a true pre-intervention baseline (nothing has been done yet) while sitting past the drop-off cliff, and it can be framed honestly:

> One last thing, and it's for you rather than us: five questions about how the last two weeks have been. In a month we'll ask again, and you'll be able to see what moved.

Users who abandon at S2 still have a working first habit. That's the correct failure mode.

### 1.3 Never at intake

- **PHQ-8 / GAD-7 — and in fact nowhere in Phase 1 (D12).** Screening someone for depression in the first ninety seconds of a wellness app is both a conversion disaster and ethically wrong-footed. But deferring it to "user-initiated" was also wrong: see §5.4. It is out of Phase 1 entirely.
- **Barrier identification as a standalone survey.** PRD §4.1.4 implies a separate obstacle inventory. It's redundant: WOOP's obstacle step captures the same construct, in the user's own words, attached to a specific habit. Cut the survey.

---

## 2. Screen-by-screen flow

```
 1. Welcome — the approach, in 25 words          10s
 2. ELM screener (3 items)                       20s
 3. Lifestyle assessment (4 items)               30s
 4. Chronotype quick (2 items)                   15s
 5. Journey recommendation + preview             20s   ← congruence check fires here
 6. Pick ONE habit                               15s
 7. ┌─ FORK (D5) ────────────────────────────────────┐
    │  "Set it up properly"      │  "Quick setup"    │
    │  7a WOOP W→O→O→P    ~75s   │  7q if-then  ~30s │
    │      (§3, 15s timers)      │      (§3.6)       │
    └────────────────────────────┴───────────────────┘
 8. Micro-habit definition                       20s
 9. Anchor selection                             20s   ← §4
10. Self-efficacy calibration (1 item)           10s
11. Plan confirmation — "here's your plan"       15s   ← VALUE MOMENT
12. WHO-5 baseline (5 items)                     40s
13. Notification permission                      10s   ← §6
    ────────────────────────────────────────────────
    proper: ~4.5 min total, ~3.2 min to value moment
    quick:  ~3.5 min total, ~2.4 min to value moment
```

**No paywall in this flow.** See §7.

---

## 3. WOOP — the core surface

This implements PRD correction C1. The whole point is that the obstacle step is not optional and outcome imagery never ships alone.

### 3.1 Hard requirements

1. **All four steps or none, within the proper path.** There is no path through the app that presents outcome imagery as a standalone exercise. If a user abandons mid-WOOP, the partial plan is discarded rather than saved as a wish-plus-outcome. Users who want speed take the quick path (§3.6) and get an honest if-then plan, not a degraded WOOP.
2. **The obstacle must be internal.** External circumstances route to coping planning instead (§3.4).
3. **Keywords for wish and outcome; a sentence for the obstacle.** 3–6 words for W and O. The obstacle has **no word limit** (D6) — see §3.2.
4. **Timed imagining, 15 seconds each** (reduced from 20, D5) for Outcome and Obstacle, with a visible but non-anxious timer. **Not skippable within the proper path** — the imagining is the active ingredient, and a WOOP with skipped timers is an if-then plan we would be mislabeling. The escape hatch is the fork at screen 7, not a skip button here.
5. **No LLM anywhere in this surface.** Consistent with the stack decision (STACK §7.3) and the failure-layer tone rules. Classification is performed by the user, not by a model (§3.4).

### 3.2 Copy deck

**Step W — Wish**

> What do you want from the next two weeks?
>
> Make it something that would genuinely be an achievement for you, and that's actually possible. Not "transform my life." Something like "walk before work most days."
>
> *[text, 3–6 words]*

**Step O — Outcome**

> Best case: you do this for two weeks. What's the single best thing about that?
>
> *[text, 3–6 words]*
>
> Now take fifteen seconds and actually picture it. Where are you, what's different, what does it feel like?
>
> *[15s timer, calm. Not skippable in this path — see §3.1 rule 4]*

**Step O — Obstacle** *(the step that makes this work)*

> Now the honest part. It's a Tuesday, you planned to do it, and you don't.
>
> What's the thing **inside you** that stops you? Not the schedule — the feeling or the thought that shows up right before you don't do it.
>
> *[text, no limit. Placeholder: "a few words is enough"]*
> *[picker: too tired · "I'll do it later" · can't be bothered · anxious about starting · resentful of the plan · don't feel like it · something else]*
>
> Fifteen seconds. Picture that moment — the actual moment you decide not to.
>
> *[15s timer]*

**No word limit on the obstacle (D6).** The protocol's keyword format serves *recall*; our use is *quotation* — we read this back to someone at the worst moment of their week. Their sentence does that work; our truncation of their sentence does not. Where the protocol and the user's own voice conflict here, the voice wins, because the mechanism we are relying on at that moment is being understood.

**Step P — Plan**

> So: **if [obstacle], then I will [   ]**.
>
> Make it something you could do while feeling exactly that way.
>
> *[3 suggestions from the class-indexed library, per failure-layer §5.3, plus free text]*

**Confirmation**

> Your plan:
>
> **When** [anchor], **I will** [habit].
> **If** [obstacle], **then I will** [response].
>
> That's it. That's the whole thing.

### 3.3 What the obstacle text is worth

The obstacle string is the highest-value field in the entire product. It is:

- quoted back verbatim in the recovery break (failure-layer §4.2, step 4)
- shown to the coach as opening context (failure-layer §8)
- the seed for coping plan generation (failure-layer §5)
- the input to the identity congruence check (§5)

**It must therefore be stored as the user typed it**, never normalized, summarized, or rewritten. When we quote it back at the worst moment of their week, it has to be *their* sentence.

### 3.4 Internal vs. external — the discrimination problem

Users overwhelmingly write external obstacles ("my kid gets sick," "work runs late"). Mental contrasting requires an internal one; external barriers need a coping plan instead, which is a different object with a different lifecycle (failure-layer §5).

**Retained, in the proper path only (D9).** Not present in quick setup — converting "work runs late" into "I feel like I've already lost the evening" is worth a screen for someone who chose the 3-minute path, and is not worth adding to a 45-second one.

**Do not classify this with a model.** Ask the user — it's cheaper, more accurate, and the asking is itself the intervention:

> *[after free-text obstacle]*
>
> Is that something that happens **around you**, or something that happens **in you**?
>
> **[Around me]** · **[In me]**

If **around me**, drill down once — this is what a trained practitioner does, and it's the step that produces the real obstacle:

> When [their external thing] happens — what happens in you? What's the feeling that makes it easy to let the plan go?

If the user still can't get to an internal obstacle after one drill-down, **accept the external one, store it as a coping-plan seed rather than a WOOP obstacle, and move on.** Do not loop. A second drill-down reads as being argued with by software, and we've already got a usable plan either way.

### 3.5 WOOP is a boost, not a nudge

WOOP is a transferable skill. After a user's third WOOP, unlock it as a standalone tool usable on anything — a work project, a difficult conversation, a habit we don't track.

This is a deliberate "boost" (competence-building) rather than a "nudge" (choice-architecture), and it's more durable. It also means we've taught the user something they keep if they cancel, which is consistent with the graduation logic in PRD §4.6.4 and is the honest version of what this product claims to be.

### 3.6 Quick setup — the honest fast path (D5)

The fork at screen 7:

> **How do you want to set this up?**
>
> **Set it up properly** · about 3 minutes. We'll work out what's actually going to get in the way, which makes the plan much harder to drop.
>
> **Quick setup** · about 45 seconds. Just the plan. We'll come back to the rest later.

Quick setup collects anchor, habit, and a plain if-then. No mental contrasting, no timers, no obstacle. The plan is stored as `plan_type = if_then` and is **not** labeled or reported internally as a WOOP.

**WOOP is then offered at the user's first lapse** (Failure Layer §4.2.1), not before.

**Why this is better than forcing the timers.** On day one the obstacle question is hypothetical, and users guess — they name the obstacle they think they should have. After a real miss they *know*, and the drill-down in §3.4 writes itself. We were asking the hardest question in the flow at the moment the user had the least material to answer it with.

The two honest options were "force the imagining" or "offer a real fast path." Forcing is worse for the user; a silently degraded WOOP is worse for everyone, because it corrupts our own measurement of whether mental contrasting works.

---

## 4. Anchor selection & the congruence check

### 4.1 Anchor selection

Rather than a free-text "when will you do this," offer candidate anchors and let the user pick:

> When will this happen? Pick something that already happens at the same time most days.
>
> **[After I wake up]** · **[After my first coffee]** · **[After I close my laptop]** · **[After dinner]** · **[Something else]**

Where calendar permission is granted, rank candidates by observed stability and say so:

> *These two are the steadiest things in your week: [X] · [Y]*

This front-loads the cue-stability logic from PRD §4.3.3 rather than waiting for the habit to fail first. **Stability scoring at creation time is worth more than stability diagnosis after two weeks of misses**, and it costs one screen.

### 4.2 Identity congruence check (PRD §4.2.2)

Fires at screen 5, using the two chronotype items from screen 4.

If a confirmed late chronotype selects a journey requiring early-morning execution:

> Quick flag before you commit to this: your answers put you on the later end of the body-clock range. The 6am version of this journey works badly for people in that range — not through lack of discipline, it's just a different clock.
>
> **[Use the later-start version]** *(recommended)* · **[Keep the early version anyway]**

Both options proceed. The check informs; it does not gate. Users who override are flagged for a day-14 check-in, because they are our highest-probability early churn.

---

## 5. Instruments

### 5.1 ELM screener (3 items, screen 2)

Routes all subsequent content per PRD §4.1.3. Presented as preference, never as capability — nothing here may read as an intelligence or effort test.

> **1.** When you try something new, would you rather:
> · Understand why it works first · Just try it and see
>
> **2.** How much time do you realistically have for this on a normal day?
> · Under 5 minutes · 5–15 minutes · More than 15
>
> **3.** Right now, how motivated are you to change something?
> · I'm ready · I'd like to but I'm not sure · Honestly, I'm just looking

**Routing:** central = (prefers understanding) AND (≥5 min available). Everything else = peripheral. Item 3 does not route content; it sets the initial ask size and is the strongest single predictor to log against D7 retention.

### 5.2 Chronotype quick (2 items, screen 4)

The µMCTQ core is mid-sleep on free days. Two items give a usable estimate:

> On days with **nothing scheduled**, what time do you usually fall asleep? *[time]*
> On those days, what time do you usually wake up **without an alarm**? *[time]*

Full MCTQ deferred to S3 (day 7). This is enough to fire the §4.2 congruence check, which is all it needs to do at intake.

### 5.3 Self-efficacy (1 item, screen 10)

Verbatim from PRD §4.1.4, habit-specific:

> How confident are you that you could do this **on your worst day this week**? *[0–10]*

Routing per PRD §4.1.4: ≤3 → force the micro-habit version and hide the full version entirely for 7 days · 4–7 → standard · ≥7 → offer to let them design their own variation.

**The ≤3 case matters most.** The correct product response to "I don't think I can do this" is to make the thing smaller, immediately and without commentary — not to encourage.

### 5.4 Deferred schedule

| Instrument | When | Framing |
|---|---|---|
| WHO-5 | End of session 1 (S2) | "So you can see what moved" |
| Full MCTQ | Day 7 | "Let's get your timing right" |
| BREQ-3 subset | Day 14 | Deliberately late — motivation quality is unstable in week 1, and measuring it during the novelty spike gives a reading that regresses regardless of what we do |
| PSS-10 | Day 30, monthly | Standard |
| ~~PHQ-8 / GAD-7~~ | **Not in Phase 1 at all (D12)** | Removed entirely — not opt-in, not in settings, not reachable |

**On removing PHQ-8/GAD-7 (D12).** v1.0 of this spec deferred them to user-initiated. That was still wrong: we would have been collecting distress data we have no ability to respond to. A user scoring 19 on a PHQ-8 is a user in trouble, and our plan was to record it and recommend a journey. Screening you cannot act on serves the research platform, not the person answering. WHO-5 is a wellbeing measure, reads as one, and creates no duty we cannot meet. Revisit in Phase 2 alongside the crisis protocol and the Guided tier, where a human is in the path.

---

## 6. Notification permission

Requested at screen 13 — **after** the plan exists, never at launch. The ask names the specific thing:

> Want a reminder at [their chosen anchor time]? We'll stop sending it once the habit sticks — that's the point.

The second sentence is not marketing. Reminder fading (PRD §4.3.5) is real, and stating it at the permission prompt is the most credible thing we say in the entire onboarding.

Declining is fully supported: the habit works, the app just won't prompt. Never re-ask more than once, and only after a `forgot`-class miss (failure-layer §5.3).

---

## 7. Paywall placement

PRD §4.1.6 says "after value demonstration, never before." This spec makes that concrete.

**The value moment is not the end of onboarding. It is the first completion.** A plan on a screen is a promise; a completed habit is evidence.

**Gate: day 7, flat (D7).** No completion requirement. No behavioral variation. Not at screen 14.

v1.0 of this spec proposed "third completion or day 5, whichever comes first." That's worse, and in a specific way: **a completion-gated paywall asks the people it is working for to pay, and lets the people it isn't working for drift away.** That inverts who we should be charging, and it makes the paywall arrive earliest for the users having the best week — which is a small betrayal of a good week.

A fixed date is also predictable enough to state plainly at signup rather than spring on someone. *Cost: slower conversion, and some carried users who were never going to pay. Accepted.*

### 7.1 Recommendation on PRD §12.5 (free-tier depth)

PRD §12 left open whether the failure layer belongs in the free tier. **It does, and I'd argue it's the whole conversion strategy.**

The reasoning: nobody converts on a feature they haven't needed yet. A user who has completed three habits has experienced our tracking, which is a commodity. A user who has *lapsed and been met well* has experienced the only thing we do that nobody else does. The recovery break is the demo.

Concretely: recovery breaks, coping plans, skip, and pause are free forever. Paid is breadth (unlimited habits, all journeys, full audio library), depth (full instrument battery, correlation insights), and people (Guided tier). This also means our most expensive-to-build feature is the one we give away — which is uncomfortable, and correct.

---

## 8. Data model

```
OnboardingSession
  id, user_id, started_at, completed_at
  abandoned_at_screen        -- the core funnel diagnostic
  elm_track                  -- central | peripheral
  elm_item3_readiness

Plan
  id, habit_id, created_at
  plan_type                  -- woop | if_then          (D5)
  created_via                -- onboarding_proper | onboarding_quick | first_lapse
  -- if_then plans populate anchor + response only; all WOOP fields null
  wish_text
  outcome_text
  outcome_imagined_seconds   -- full 15 in proper path; null for if_then
  obstacle_text              -- VERBATIM, unbounded length. never normalized (§3.3, D6)
  obstacle_class             -- internal | external_accepted
  obstacle_source            -- freetext | picker | after_drilldown
  obstacle_imagined_seconds
  plan_response_text
  drilldown_used             -- bool
  superseded_by              -- WOOP is re-runnable; keep the chain

ChronotypeEstimate
  user_id, free_sleep_onset, free_wake_time
  midsleep_free, estimated_at, source  -- quick2 | full_mctq
  congruence_flag_shown, congruence_overridden
```

`outcome_imagined_seconds` and `obstacle_imagined_seconds` exist because the imagining is the mechanism. Under D5 the timers are no longer skippable within the proper path, so these should read a clean 15 — their job is now to catch backgrounding, force-quits, and any future "skip" that creeps back in during implementation.

`plan_type` is the field that keeps us honest: it is what prevents an if-then plan from being counted as mental contrasting in §9 metrics or in the §8.8 research platform.

---

## 9. Metrics

| Metric | Definition | Why |
|---|---|---|
| **Time to value moment** | Start → plan confirmation | Target < 4 min |
| Onboarding completion | Reached screen 11 | Target > 65% |
| Screen-level drop-off | Per screen | WOOP is the suspect; watch screens 7a–7d individually |
| **Fork split** | % choosing proper vs. quick (D5) | If quick > 80%, the proper path's framing needs work — or WOOP genuinely belongs at first lapse for nearly everyone, which is also a finding |
| **Quick→WOOP conversion** | % of `if_then` users accepting WOOP at first lapse | The direct test of D5's core claim: that the obstacle question lands better once there's a real obstacle |
| **Obstacle capture rate** | Non-empty, internal-class obstacle, among proper-path plans | Target > 70%. Below that, WOOP isn't working and the recovery break loses its best material |
| Internal vs. external split | Pre- and post-drilldown | Measures whether §3.4's drilldown earns its screen |
| **Imagining completion** | % completing both 15s timers | Should be ~100% post-D5; a shortfall means a skip path leaked back in |
| First completion within 24h | | The real onboarding outcome |
| D7 retention by ELM track | | Validates §5.1 routing |
| D7 retention by congruence override | | Validates §4.2 |

### 9.1 First onboarding experiment

This is the direct test of PRD correction C1, and it should run early because it's the correction with the most product surface riding on it.

| Arm | Content |
|---|---|
| **A** | Full WOOP (wish, outcome+imagery, obstacle+imagery, plan) |
| **B** | Action plan only — if-then, no mental contrasting, no imagery |
| **C** | Outcome + plan, **no obstacle step** |

Arm C is included specifically because it's what most competitors ship and what v1.0 originally specified. The literature predicts C ≤ B < A. If C outperforms, C1 was wrong and the PRD needs revisiting — which is exactly the kind of finding §5.2's rejected-mechanisms register commits us to publishing.

**Primary outcome:** habit still active at day 30. **Secondary:** lapse recovery rate (failure-layer §11.1), obstacle capture rate, onboarding completion.

**D5 makes this cleaner, not messier.** Arm B is now a *shipping path* (quick setup, §3.6) rather than a synthetic condition, which means we get its data from natural fork choice as well as from randomization — and it means the experiment no longer requires deliberately giving some users a worse experience than we'd otherwise ship. Randomize the fork's *default emphasis* rather than withholding a path.

**Powering note:** unlike the failure-layer MRT, this is a user-level A/B and will need real volume. Budget for it to be inconclusive at Phase 1 scale, and design the logging so it can be pooled across the first two quarters. Self-selection into the fork confounds the naturalistic comparison — the randomized arm is what carries the causal claim.

---

## 10. Edge cases

| Case | Handling |
|---|---|
| Can't name any obstacle | Picker, then accept "don't feel like it" as a legitimate answer. It is one |
| Abandons mid-WOOP | Discard the partial plan (§3.1 rule 1). On return, offer **quick setup** rather than restarting WOOP — they already told us, by leaving, that the long path wasn't right today. WOOP returns at first lapse per §3.6 |
| Picks a journey wildly misaligned with stated time budget | Congruence check with the shorter variant offered. Never block |
| Self-efficacy ≤3 on everything | Reduce to a single 2-minute habit and say so plainly: "Let's start with one small thing." No motivational commentary |
| Returns after 30 days having never completed a habit | Do not resume onboarding. Fresh start (PRD §4.1.5) — new WOOP, new habit |
| Screen reader | WOOP timers must not steal focus; the imagining prompt is read, then the timer runs silently with a completion announcement |
| Reduced motion | The timer is a numeric countdown, not an animated ring |
| Minor / age gate | Age gate at screen 1. Under-16 EU / under-13 US routes out entirely — we have no parental-consent infrastructure, and PRD §8.9 family features do not change that until built |

---

## 11. Acceptance criteria

Launch-blocking:

- [ ] Time to value moment < 4 minutes at p50 on the proper path, < 3 min on quick, measured on real devices
- [ ] No path in the app presents outcome imagery outside the four-step sequence
- [ ] Partial WOOP is discarded, not saved; abandonment offers quick setup on return
- [ ] **Fork present at screen 7; quick setup stores `plan_type = if_then` and is never counted as WOOP** (D5)
- [ ] **Imagining timers are not skippable within the proper path** (D5)
- [ ] Obstacle text is stored verbatim and unbounded; verified by inspecting stored rows against typed input (D6)
- [ ] Internal/external discrimination is user-performed; no model in this surface
- [ ] Drilldown loops at most once, and is absent from quick setup (D9)
- [ ] WHO-5 fires after plan confirmation, before any habit completion
- [ ] **PHQ-8/GAD-7 do not exist in the Phase 1 build** — not gated, not hidden, absent (D12)
- [ ] **No paywall before day 7** (D7)
- [ ] Notification permission requested at screen 13, never at launch, and names the specific anchor time
- [ ] Congruence check informs and never blocks
- [ ] Screen-level funnel instrumentation live for screens 7a–7d individually
- [ ] Age gate at screen 1

---

## 12. Open questions — resolved

All five are closed in DECISIONS-v1.

| v1.0 question | Resolution |
|---|---|
| 1. Do the imagining timers survive contact with users? | **Closed — D5.** Sidestepped rather than answered. Timers are non-skippable within the proper path and shortened to 15s; users who want speed take the quick path and get an honest if-then plan. A silently degraded WOOP was the outcome worth avoiding, because it would have corrupted our own measurement |
| 2. Is 3–6 words too tight for the obstacle? | **Closed — D6.** No limit. The protocol's keyword serves recall; our use is quotation |
| 3. Does the drilldown earn its screen? | **Closed — D9.** Kept in the proper path, absent from quick setup. Still instrumented (§9) — if internal obstacles don't outperform, revisit |
| 4. Paywall timing | **Closed — D7.** Day 7, flat. Completion-gating charges the people it's working for and lets the strugglers drift |
| 5. Free-tier failure layer | **Closed — D8.** Free forever, including after cancellation. PRD §4.9 |

**Nothing in this spec is blocked on a decision.** What remains is measurement: the fork split and quick→WOOP conversion rates (§9) tell us within a quarter whether D5's central claim — that the obstacle question lands better once there's a real obstacle — is right.
