# Build Spec — Habit Engine

**Implements:** PRD §4.3 (routine builder, cue stability, reminder fading), §4.6.4 (graduation), §9.2 (unprompted completion)
**Phase:** 1 — blocking for launch
**Version:** 1.0
**Date:** 8 August 2026
**Incorporates:** D10 (graduation non-negotiable), D11 (stability at creation, never at failure)

> **What this owns.** Onboarding (SPEC-onboarding) hands off a habit with a plan. The failure layer (SPEC-failure-layer) picks up when one is missed. Everything between — anchors, scheduling, prompting, fading, graduation — is here. Two named differentiators live in this document: cue-stability scoring and habit graduation. So does the primary success metric.

---

## 1. Object model

```
Habit
  id, user_id, journey_id (nullable)
  title, full_version, micro_version      -- micro defined at creation, never improvised
  anchor_id
  plan_id                                 -- woop | if_then (Onboarding §8)
  state                                   -- forming | established | graduated |
                                             lapsed_* | dormant | paused | retired
  fade_level                              -- L0..L4, see §5
  created_at

Anchor
  id, user_id
  class                                   -- wake | first_coffee | commute_start |
                                             lunch | work_end | dinner | bedtime | custom
  label                                   -- user-facing text
  nominal_time                            -- local wall clock, may be null for event anchors
  stability                               -- see §3; recomputed nightly
  stability_basis                         -- prior | calendar | observed

Occurrence
  id, habit_id, scheduled_local           -- wall clock, not UTC (§4.2)
  window_start, window_end
  prompt_policy                           -- prompt | suppress | probe   (§5.3)
  prompt_sent_at                          -- nullable
  completed_at                            -- nullable
  completion_source                       -- app | widget | watch | integration
  unprompted                              -- computed, see §6
  outcome                                 -- completed | skipped | missed | rest
```

`full_version` and `micro_version` are both mandatory at creation. The two-minute version defined calmly on day one is a different and much better artifact than one improvised at the bottom of a bad week.

---

## 2. Anchors

### 2.1 Anchors are objects, not strings

A habit points at an anchor; several habits may share one. This is what makes stacking work (§7) and what lets a single "your morning coffee has moved" insight apply to everything hanging off it.

### 2.2 Candidate generation at creation

Onboarding §4.1 offers anchor candidates rather than a free-text time. Candidates come from, in order:

1. **Anchor class priors** (§3.4) — always available, zero data required
2. **Calendar-derived stability** — where permission granted
3. **Observed stability** — only for anchors the user already has

Custom anchors are allowed but are scored `prior`-only until 14 days of data exist, and the UI says so rather than implying we know something we don't.

---

## 3. Cue-stability scoring

**Placement is fixed by D11: creation and re-planning only. This score must never appear in the recovery break.** The same sentence is help before you commit and a verdict on your life afterwards.

### 3.1 Report the weakest dimension, never a composite

Three dimensions are measured. **We do not average them into a single score**, because we cannot validate the weights and a composite hides the actionable part. We report the worst one and what to do about it.

| Dimension | Measure | Stable | Variable | Unstable |
|---|---|---|---|---|
| **Temporal** | Circular MAD of completion time-of-day, trailing 14 occurrences | < 30 min | 30–75 min | > 75 min |
| **Locational** | Share of occurrences in the modal location cluster | > 0.75 | 0.5–0.75 | < 0.5 |
| **Calendar** | Share of days where the surrounding 60-min block has the same free/busy shape | > 0.7 | 0.45–0.7 | < 0.45 |

**Circular statistics are required for the temporal dimension.** Times of day wrap at midnight; a naive standard deviation over 23:50 and 00:10 returns twelve hours of spread for a twenty-minute one. Use the circular mean, then median absolute deviation about it for robustness against the occasional 3am outlier.

### 3.2 Minimum data

- **< 5 observed occurrences:** no observed score. Fall back to calendar, then priors. Basis is shown to the user.
- **5–13:** provisional, wider thresholds (temporal stable < 45 min).
- **≥ 14:** full scoring.

Never show a stability verdict computed from fewer than five points as though it were established.

### 3.3 What the user sees

At creation, on the anchor picker:

> *Steadiest things in your week:* **[after I wake up]** · **[the school run]**
> *[after lunch] varies by about 90 minutes — that's a hard thing to attach to.*

At re-planning after a lapse — **only when the user is re-planning, never as a lapse response:**

> Before you set this up again: this anchor moved by an hour and a half most days last month. That's usually why a habit like this doesn't stick, and it isn't a discipline problem.

### 3.4 Anchor class priors

Used at cold start, and honestly labeled as priors. Ordered most to least stable in typical data:

| Class | Prior | Rationale |
|---|---|---|
| `wake` | Stable | Anchored to sleep, itself fairly regular even in irregular lives |
| `bedtime` | Variable | High evening variance is the norm, not the exception |
| `first_coffee` | Stable | Usually tightly coupled to wake |
| `commute_start` | Stable on weekdays, absent otherwise | Flag as weekday-only |
| `work_end` | Variable | The single most over-trusted anchor users pick |
| `lunch` | Variable | Meeting-driven |
| `dinner` | Variable | Household-dependent |

These are defaults to be replaced by observation, not findings. Validate against our own cohort at 6 months and update the table — that is a §8.8 candidate.

### 3.5 Privacy

Location clustering runs **on-device**. Only the resulting cluster-share statistic leaves the phone — never coordinates, never a cluster centroid. This is required by PRD §6.2's on-device preference and is also the difference between "we score your anchor stability" and "we keep a record of where you are each morning."

If location permission is denied, the locational dimension is simply absent. The feature degrades to two dimensions and says nothing about it.

---

## 4. Scheduling

### 4.1 Occurrence generation

Occurrences are materialized 7 days ahead by a nightly job, so that prompt policy (§5.3) can be assigned in advance and probe days can be planned rather than decided at fire time.

### 4.2 Wall clock, not UTC

`scheduled_local` is a local wall-clock time plus a timezone identifier. A 07:00 habit is at 07:00 through a DST transition, and it is at 07:00 local after the user flies to Lisbon.

Three failure modes this avoids, all of which are routine in this category:
- Storing UTC and shifting everyone's morning routine by an hour twice a year
- Generating a duplicate or missing occurrence on the transition day
- Prompting someone at 4am on their first morning abroad

### 4.3 Travel

Timezone change of ≥2 hours detected → **stability scoring pauses** for that user and resumes 3 days after the timezone stabilizes. Travel makes every anchor look unstable, and it is exactly the wrong moment to tell someone their life is too irregular.

Occurrences continue on local wall clock. This is a deliberate choice: for most habits, local-time continuity is what the user wants, and the ones where it isn't (sleep timing) belong to journey logic rather than the engine.

### 4.4 Windows and grace

Default window is the anchor's nominal time ± 90 minutes, widened to ±3 hours for anchors scoring Variable or Unstable. **A wider window on an unstable anchor is not leniency — it is an accurate model of when the cue actually occurs.** Miss detection then follows SPEC-failure-layer §1.2 (window close + 2h, never 22:00–07:00).

---

## 5. Prompting and reminder fading

The design goal, per PRD §4.3.5: a habit that only fires on notification is not a habit, it is compliance with our notification. Fading is therefore the planned end state, and we say so at the permission prompt (Onboarding §6).

### 5.1 The ladder

| Level | Prompt frequency |
|---|---|
| L0 | Every occurrence |
| L1 | 5 in 7 |
| L2 | 3 in 7 |
| L3 | 1 in 7 |
| L4 | None |

New habits start at L0. `forgot`-class coping plans (SPEC-failure-layer §5.3) may drop a habit back to L0 for exactly 7 days, then it resumes its prior level — this is the one sanctioned way back up, and it is time-boxed so fading doesn't unravel through the coping-plan door.

### 5.2 Advancement and regression

- **Advance** one level after **3 consecutive unprompted completions** at the current level.
- **Regress** one level on entry to `lapsed_2`. **One level, never to L0.** Regression is a support adjustment, not a penalty, and dropping someone to daily prompts after a bad week reads as one.
- No advancement while in any lapsed or paused state.

### 5.3 Probe days — the measurement instrument

**At every level including L0, one occurrence per week is randomly designated a probe: the prompt is deliberately withheld.**

This is the only way to distinguish *"completed because we reminded them"* from *"would have completed anyway."* Without withholding, unprompted-completion rate is unmeasurable at L0–L1, which is precisely where we most need to know whether automaticity is forming.

**Constraints — this is deliberately withholding help, so it is fenced:**

- Never during `lapsed_*`, `dormant`, or `paused`
- Never in a habit's first 7 days
- Maximum 1 per habit per week, and maximum 2 per user per week across all habits
- Never on a probe day for two consecutive weeks in the same weekday slot (avoids systematically sabotaging someone's Tuesdays)
- A probe miss is recorded as a **probe miss** and does **not** count toward `lapsed_*` progression or streak loss

That last rule matters: we caused it, so we absorb it.

### 5.4 Prompt content

The prompt names the habit and the anchor, nothing else. No streak counts, no percentages, no encouragement — the same discipline as SPEC-failure-layer §6 rule 6.

> **After your morning coffee: two-minute stretch.**

At L3–L4, prompt copy shifts from instruction to check-in, because by then we are asking rather than reminding:

> Still doing the morning stretch? *[Yes]* · *[Not lately]*

---

## 6. Unprompted completion — the primary metric

**Definition:** a completion where no prompt was delivered for that occurrence, or where the completion timestamp precedes the prompt delivery timestamp.

### 6.1 Attribution rules

| Situation | Unprompted? |
|---|---|
| No prompt sent (probe, or L1–L4 non-prompt occurrence) | **Yes** |
| Prompt sent, completion logged before delivery | **Yes** |
| Prompt sent and delivered, completion after | No |
| Prompt sent, device offline, delivered late, completion before delivery | **Yes** — delivery time governs, not send time |
| Completion from widget or watch with no app open | Judged by prompt delivery only, same rules |
| Habit completed twice (duplicate log) | First completion governs |

Delivery time rather than send time is the whole subtlety here. A prompt sent at 07:00 and delivered at 09:40 when the phone came off airplane mode did not cause an 08:15 completion.

### 6.2 Reporting

Report unprompted rate **at the habit level and only over probe-eligible occurrences** when comparing across fade levels — otherwise the metric trivially rises with fading and tells us nothing about automaticity.

---

## 7. Stacking

A chain is an ordered list of habits sharing one anchor:

> After **[morning coffee]** → water → stretch → intention

**Rules:**
- Maximum 3 habits per chain at launch. Longer chains fail as a unit and are a common way for users to lose four habits at once.
- Only the **first** habit in a chain is prompted. The rest are cued by the preceding habit — that is the entire mechanism, and prompting each one separately destroys it.
- Fading applies to the chain's head habit; the tail never had prompts to fade.
- If the head habit graduates, prompting for the chain ends entirely. The chain is by then a single behavioral unit, which is the intended outcome.
- A habit may be added to a chain only if the chain's anchor scores Stable or Variable. Building a three-link chain on an unstable cue is a designed failure.

---

## 8. Goal-conflict detection

Nightly, over the 7-day materialized horizon:

- **Hard conflict:** two occurrences overlap, or an occurrence sits inside a calendar block marked busy
- **Soft conflict:** three or more occurrences within a 30-minute span

Surfaced **before** the day, never after the miss:

> Tomorrow's a squeeze — your walk and your 8:30 call are on top of each other. Move the walk to the evening, or skip it tomorrow?
> **[Move]** · **[Skip tomorrow]** · **[Leave it]**

A pre-emptive skip taken here is a `rest` outcome, not a miss. The user made a plan; that is the behavior we want.

---

## 9. Graduation (D10)

### 9.1 Criteria

All three, simultaneously:

1. **SRBAI** at or above threshold on two consecutive biweekly measures
2. **Fade level L4** (no scheduled prompts)
3. **≥ 80% completion over the trailing 30 days**, measured on probe-eligible occurrences

### 9.2 What happens

- Habit moves to `graduated`. Prompts stop permanently.
- It leaves the active list and appears in a "kept" section.
- Maintenance check at 30 and 90 days: a single question, once, no nagging.

> Still going with the morning stretch? *[Yes]* · *[It's slipped]*

- "It's slipped" **offers** re-entry to `forming`. It never forces it, and it never re-enables prompts without consent.

### 9.3 The celebration is the point

Graduation is the strongest positive moment the product has, and it must not be a quiet state change:

> **This one's yours now.**
> Fourteen weeks. The last thirty days you did it without a single reminder from us — that's the definition we use, and you've met it. We'll stop bringing it up.

We are the only product with an incentive to say this. Saying it well is most of the value of D10.

---

## 10. Metrics

| Metric | Definition |
|---|---|
| **Unprompted completion rate** | §6 — primary success metric per PRD §9.2 |
| Fade level distribution | Users' habits by L0–L4; a population stuck at L0 means fading isn't working |
| Time to L4 | Median days from creation |
| Graduation rate | Habits reaching `graduated` |
| Probe completion rate | Completion on withheld-prompt days — the cleanest automaticity read we have |
| Anchor stability at creation | Distribution, by class — validates §3.4 priors |
| Stability→survival correlation | Does a Stable anchor at creation predict day-30 survival? **This is the load-bearing validation for the whole cue-stability feature** |
| Chain survival vs. singleton | Do 3-habit chains outlive single habits, or fail as a unit? |

---

## 11. Acceptance criteria

Launch-blocking:

- [ ] Occurrences generated in local wall clock; verified across a DST transition in both directions
- [ ] Verified across a simulated timezone change: no 4am prompts on arrival
- [ ] Temporal stability uses circular statistics; unit test with times spanning midnight
- [ ] Stability score never rendered anywhere in the recovery-break surface (D11)
- [ ] Stability basis (`prior` / `calendar` / `observed`) shown to the user, never implied as observed when it isn't
- [ ] Location clustering runs on-device; verified that no coordinates leave the client
- [ ] Probe days respect all five §5.3 constraints; probe misses excluded from lapse progression
- [ ] Unprompted attribution uses prompt **delivery** time; test with a delayed-delivery case
- [ ] Only the head habit of a chain is prompted
- [ ] Graduation stops prompts permanently and does not re-enable them without explicit consent
- [ ] Fade regression is one level, never to L0
- [ ] `forgot`-class prompt restoration expires after exactly 7 days

---

## 12. Open questions

1. **Are the §3.1 thresholds right?** 30/75 minutes for temporal stability is drawn from what feels like a meaningful cue window, not from data. The stability→survival correlation in §10 recalibrates them, and it is the first analysis to run once we have 90 days of data.
2. **Do probe days cost more than they measure?** We are deliberately withholding help from a user roughly once a week to make a metric computable. The fences in §5.3 keep it small, but if probe-day misses turn out to predict churn, the honest response is to lower the probe rate and accept a noisier primary metric — not to keep the metric and absorb the harm.
3. **Is 3 habits the right chain cap?** Chosen conservatively. §10's chain-survival comparison answers it.
4. **Should graduation be reversible on our initiative?** Currently the 30/90-day check asks, and only the user can re-activate. The alternative — detecting decay from integrations and offering re-entry — is more helpful and also more paternalistic. Leaving it user-initiated until there's evidence people want otherwise.
