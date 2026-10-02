# Build Spec — Journey Library

**Implements:** PRD §4.2 (journey architecture, library), §4.2.4 (dCBT-I safety gate)
**Phase:** 1 — blocking for launch
**Version:** 1.0
**Date:** 8 August 2026
**Incorporates:** D4 (Unhook scope), D12 (no clinical screening in Phase 1)

> **Scope of this document.** Journey architecture, the day template, the journey↔engine and journey↔failure-layer interfaces, one journey specified in full as the reference implementation (Sleep Reset — it carries the safety gate and the strongest evidence base), and BCT-tagged outlines for the other five. It is not the content itself; §9 defines who writes and reviews that.

---

## 1. What a journey is

A journey is a **sequenced program that installs habits into the engine and then gets out of the way.** It is not a content playlist with a progress bar.

Concretely, a journey does four things and nothing else:

1. Introduces habits, on a schedule, into the habit engine (SPEC-habit-engine)
2. Delivers a daily lesson that explains the mechanism behind today's ask
3. Prompts a reflection that produces data we can use
4. Ends — leaving behind habits that outlive it

Point 4 is the design constraint that separates this from every content-library competitor. A journey that has to keep running for its habits to survive has failed, in the same way and for the same reason as a habit that never leaves L0 prompting.

```
Journey
  id, slug, title, duration_days
  safety_gate_id            -- nullable; blocking if present (§5.1)
  bct_tags[]                -- required, see §2

JourneyDay
  journey_id, index         -- 1..duration_days
  lesson_id
  habit_actions[]           -- introduce | modify | retire
  reflection_prompt_id
  bct_tags[]

JourneyEnrollment
  user_id, journey_id
  current_index             -- advances on completion, NOT calendar (§4)
  started_at, completed_at
  gate_result               -- passed | routed_out | variant_assigned
  variant                   -- nullable; e.g. sleep_reset_no_restriction
```

---

## 2. BCT tagging is a build requirement

Per PRD §4.2.1, every journey and every day carries tags from the **Behaviour Change Technique Taxonomy v1** (Michie et al., 2013 — 93 techniques, 16 clusters).

This is not documentation. It is what makes three things possible:

- **Coverage audit.** A 28-day journey that turns out to be 24 days of "5.1 Information about health consequences" is a podcast, and tagging is how we find that out before shipping rather than after.
- **Technique-level experimentation.** §8.8's MRTs randomize at the technique level; without tags there is nothing to randomize over.
- **Honest answers.** When someone asks why a journey works, the answer is a list of techniques with an evidence grade each, not a paragraph of adjectives.

**Constraint:** no journey ships with fewer than 6 distinct BCTs, and no single BCT may account for more than 40% of tagged days.

---

## 3. The day template

Every journey day has the same anatomy. Users get variety from content, never from structure — a program whose shape changes daily costs attention that should go to the behavior.

| Slot | Budget | Purpose | Optional? |
|---|---|---|---|
| **Today's ask** | — | The habit action. Often nothing new | No |
| **Lesson** | 90–180s read, or 2–3 min audio | Why today's ask works | No |
| **Reflection** | 1 question | Produces data, not journaling for its own sake | Yes, from day 4 |
| **Deep dive** | 8–15 min | Central ELM track only (Onboarding §5.1) | Yes |

**Budget discipline:** total daily journey time ≤ 5 minutes, excluding the habit itself. A journey that costs more than the habits it installs has inverted its own purpose.

### 3.1 Reflection prompts must earn their place

Each prompt maps to a field we use. Prompts that generate only prose are cut.

| Prompt | Feeds |
|---|---|
| "What time did you actually do it?" | Cue stability (engine §3) |
| "What nearly stopped you today?" | Coping-plan seeding (failure-layer §5) |
| "How automatic did that feel?" | SRBAI, on schedule |
| "Which version did you do — full or small?" | Shrink tracking (D2) |

---

## 4. Journeys advance on completion, not calendar

**Decision.** `current_index` increments when the user completes a day, not when the sun sets.

A user who misses three days of a 28-day journey is on day 12 of 28, not day 15 with three holes. The alternative compounds: falling behind becomes visible, then becomes a deficit, then becomes a reason to quit — which is the abstinence violation effect wearing a progress bar.

**Consequences, all intended:**
- Journeys have no end date, only a length
- "Day 14 of 28" always means fourteen days of work done
- No catch-up mechanics, no "you're behind" state, no missed-day backfill

**The one exception is Sleep Reset**, where the protocol is genuinely time-coupled — sleep-window titration depends on consecutive nights of diary data (§5.4). It handles gaps explicitly rather than by pretending they didn't happen.

### 4.1 Interface with the failure layer

Journey progress and habit lapse are **separate systems that must not be wired together**:

- Missing a habit does not stall the journey
- Skipping a journey day does not mark the habit missed
- The recovery break never mentions journey progress — that would be a completion percentage at the worst moment, prohibited by failure-layer §6 rule 6

A journey with no activity for 10 days goes `dormant` and follows the same rules as a dormant habit: one re-entry offer at the next temporal landmark (PRD §4.1.5), then silence.

---

## 5. Sleep Reset — reference implementation

**Duration:** 28 days · **Evidence grade: Strong** (dCBT-I; SHUTi and Sleepio RCTs) · **Safety gate: blocking**

This is the strongest evidence base available to a consumer wellness app, which is precisely why it carries the most safety machinery. v1.0 of the PRD specified this journey as sleep hygiene, which is the *weakest* CBT-I component and the one most likely to produce a null result.

### 5.1 Safety gate (blocking — PRD §4.2.4)

Runs before enrollment. Cannot be skipped, cannot be dismissed, cannot be reached around.

| Screen for | Action if positive |
|---|---|
| Bipolar disorder or history of mania/hypomania | **Route out.** Sleep restriction can precipitate mania |
| Seizure disorder / epilepsy | **Route out.** Sleep deprivation lowers seizure threshold |
| Occupational driving, heavy machinery, safety-critical shift work | **Route out.** Restriction increases daytime sleepiness before it improves sleep |
| Obstructive sleep apnea risk (STOP-BANG ≥ 3) | **Route out** to "discuss with a doctor first" — restriction does not treat OSA and can worsen it |
| Pregnancy | **Variant.** No restriction component |
| Parasomnias (sleepwalking, night terrors) | **Route out** |
| Under 18 | **Route out** — protocol and evidence are adult-derived |

**Routing out is not a rejection.** Users who screen out are offered the **stimulus-control-and-light variant**: consistent wake time, bed-for-sleep-only, morning light, worry time. No sleep-window compression. This variant retains real evidence and carries no contraindications, and it is presented as a different route rather than a consolation.

**Copy discipline at the gate:** these questions arrive early and are alarming if handled badly. Frame as fit, not diagnosis:

> A few questions first — this program involves changing when you're in bed, and for some people that's the wrong tool. Ninety seconds.

Never: "Do you suffer from…". Never a results screen that reads as a diagnosis.

### 5.2 Protocol components, in evidence order

| Component | BCT tags | Notes |
|---|---|---|
| **Sleep diary** | 2.3 Self-monitoring of behaviour | Days 1–7 baseline, then continuous. Also the titration input |
| **Sleep compression** | 8.1 Behavioural practice; 1.1 Goal setting | *Compression, not aggressive restriction* — see §5.3 |
| **Stimulus control** | 12.3 Avoidance/reducing exposure to cues; 8.3 Habit formation | Bed for sleep only; out of bed if awake ~20 min; fixed wake time; no naps |
| **Constructive worry** | 11.2 Reduce negative emotions; 1.2 Problem solving | Scheduled worry time, early evening, on paper |
| **Cognitive restructuring** | 13.2 Framing/reframing | Unhelpful beliefs about sleep (catastrophizing about tomorrow) |
| **Morning light** | 12.1 Restructuring the physical environment | Chronotype-adjusted via MCTQ |
| **Sleep hygiene** | 4.1 Instruction on how to perform | **Last, and framed as least important.** Leading with it is the standard mistake |

### 5.3 Sleep compression, not restriction — and the floor

Clinical sleep restriction sets time-in-bed to measured total sleep time, which can mean an initial window of 5 hours and a genuinely rough first week under clinician supervision. **We are not a clinician and the user is alone with their phone.**

**Consumer adaptation:**
- Start window = average total sleep time **+ 30 minutes**, not TST exactly
- **Hard floor: 5.5 hours. The algorithm may never propose a window below this, regardless of what the diary says.**
- Compress toward the target by 15 minutes every 3 days rather than in one step
- Fixed wake time; the window moves at the bedtime end only

**Titration rule** (sleep efficiency = total sleep time ÷ time in bed, trailing 5 nights):

| SE | Action |
|---|---|
| ≥ 90% | Extend window 15 min |
| 85–90% | Hold |
| < 85% | Compress 15 min, subject to the 5.5h floor |

**Daytime sleepiness check on days 5, 10, 15.** A single item. If the user reports severe sleepiness or any driving impairment, **the window auto-extends 30 minutes and the journey says so plainly.** This overrides the titration rule. Sleepiness is the known adverse effect of this protocol and it is the one that hurts people outside the app.

### 5.4 Handling gaps (the §4 exception)

Titration needs consecutive nights. If diary data is missing for 2+ of the trailing 5 nights:

- Titration **pauses**; the window holds where it is
- The journey continues; lessons and other components proceed
- No catch-up, no backfill request beyond one gentle "last night?" prompt

Never titrate on imputed sleep data. A window computed from a guess is a real intervention derived from a fiction.

### 5.5 Arc

| Days | Focus | Habits introduced |
|---|---|---|
| 1–7 | Baseline diary. **No behavior change asked.** Lessons cover how sleep actually works, why hygiene is oversold | Sleep diary |
| 8–10 | Fixed wake time + morning light | Wake time, light exposure |
| 11–17 | Stimulus control; window compression begins day 12 | Out-of-bed rule, no-nap rule |
| 18–24 | Constructive worry; cognitive restructuring | Worry time |
| 25–28 | Consolidation, titration handover, relapse planning | — |

**Days 1–7 ask for no change at all.** Baseline data is required, self-monitoring is itself an active ingredient (Harkin et al. 2016), and a week of noticing before changing is also how you earn the right to ask for something hard on day 12.

### 5.6 Exit

The journey ends by handing titration to the user:

> You know how this works now. Sleep efficiency over 90% for five nights, add fifteen minutes. Under 85%, take fifteen off — never below five and a half hours. That's the whole algorithm, and it's yours.

Fixed wake time and morning light continue as engine habits and proceed toward graduation normally. The diary drops to weekly.

---

## 6. The other five

Outlines with BCT coverage. Content production per §9.

### 6.1 Deep Work Protocol · 14 days · Evidence: Moderate

| Week | Arc | Key BCTs |
|---|---|---|
| 1 | Measure attention baseline; environment restructuring; single-tasking blocks | 2.3 Self-monitoring · 12.1 Physical environment · 12.3 Reducing cue exposure |
| 2 | Time blocking; inhibitional if-then plans for distraction; temptation bundling | 1.4 Action planning · 15.3 Focus on past success · 7.1 Prompts/cues |

**Habits installed:** one distraction-free block, one shutdown ritual.
**Note:** inhibitional implementation intentions ("if I reach for my phone, then I put it in the drawer") are the mechanism here — same class as Unhook, d ≈ 0.65 in the Gollwitzer & Sheeran meta-analysis.

### 6.2 Mood Activation · 30 days · Evidence: Strong

Behavioral activation, which is a standalone evidenced treatment and structurally identical to what the engine already does.

| Week | Arc | Key BCTs |
|---|---|---|
| 1 | Activity + mood monitoring with **mastery and pleasure ratings** | 2.3 Self-monitoring · 2.4 Self-monitoring of outcomes |
| 2 | Values clarification → activity menu | 1.1 Goal setting · 13.1 Identification as role model |
| 3 | Graded activity scheduling from the menu | 1.4 Action planning · 8.1 Behavioural practice |
| 4 | Avoidance patterns; TRAP→TRAC; relapse planning | 1.2 Problem solving · 8.2 Behaviour substitution |

**Critical constraint (D12):** this journey is *not* a depression treatment claim and must not be marketed as one. No PHQ-8, no severity scoring, no "clinically proven" language. It is activity scheduling with mastery/pleasure ratings, which is what it says it is. Revisit the claim only alongside the crisis protocol.

**Copy safety:** low mood makes lapse copy land harder. This journey inherits the failure-layer tone rules with one addition — no "just do it anyway" framing anywhere, which is the single most common way BA content goes wrong in consumer adaptations.

### 6.3 Energy Engineering · 28 days · Evidence: Moderate

| Week | Arc | Key BCTs |
|---|---|---|
| 1 | Movement snacks — short vigorous bouts (VILPA framing) | 8.1 Behavioural practice · 8.3 Habit formation |
| 2 | Circadian alignment: light, meal timing anchors | 12.1 Physical environment · 7.1 Prompts/cues |
| 3 | Energy–activity correlation from own data | 2.4 Self-monitoring of outcomes · 2.2 Feedback on behaviour |
| 4 | Consolidation into a daily shape | 8.3 Habit formation |

**Do not make nutrition claims.** Meal *timing* as a circadian anchor is defensible; nutrition content is out of scope and out of our competence.

### 6.4 Confidence Building · 21 days · Evidence: Moderate

| Week | Arc | Key BCTs |
|---|---|---|
| 1 | Mastery logging; small wins bank | 2.3 Self-monitoring · 15.3 Focus on past success |
| 2 | Graded social exposure, self-selected ladder | 8.1 Behavioural practice · 11.1 Pharmacological — *n/a, omitted* |
| 3 | Self-affirmation; identity statements (PRD §4.2.2) | 13.5 Identity associated with behaviour |

**Power posing is not in this journey (PRD §5.2).** The hormonal claims failed replication; only self-reported felt power survived, and that is not worth a day of a 21-day program.

### 6.5 Unhook · 21 days · Evidence: Strong for the technique, Moderate in this application

Habit reversal training. **Phase 1 scope is digital and behavioral targets only (D4)** — the category picker excludes substances, alcohol, and anything adjacent to disordered eating.

| Week | Arc | Key BCTs |
|---|---|---|
| 1 | Awareness training — log occurrence + antecedent. **No change asked** | 2.3 Self-monitoring · 2.2 Feedback |
| 2 | Environment first: stimulus control, then competing response | 12.3 Reducing cue exposure · 8.2 Behaviour substitution |
| 3 | Inhibitional if-then plans; social support; maintenance | 1.4 Action planning · 3.1 Social support |

**Week 2 leads with environment design even though it means the user opens our app less.** For digital-behavior quits, stimulus control outperforms every willpower technique, and saying so is the credibility position from PRD §4.7.

---

## 7. Journey → engine interface

Journeys create and modify habits through a narrow API. They never write engine state directly.

```
introduce_habit(journey_id, day_index, spec)  -- creates at fade L0, forming
modify_habit(habit_id, field, value)          -- e.g. widen sleep window
retire_habit(habit_id, reason)                -- journey-initiated, user-confirmable
```

**Rules:**
- A journey may introduce at most **one habit per day** and **five per journey**. More is a to-do list.
- Journey-introduced habits are ordinary habits: they fade, they lapse, they graduate. Nothing about them is special-cased.
- **When a journey ends, its habits persist.** This is the entire point of §1 item 4.
- A journey may never re-enable prompts on a graduated habit (engine §9.2).

---

## 8. Content production

| Content type | Author | Reviewer | Sign-off |
|---|---|---|---|
| Lesson copy | Content writer | Behavioral advisor | Advisor |
| Any efficacy claim | — | Advisor against PRD §5.1 grades | **Advisor, mandatory** |
| Sleep Reset, all | Content writer | **Sleep clinician** | **Clinician, blocking** |
| Mood Activation, all | Content writer | Clinical psychologist | **Clinician, blocking** |
| Unhook, all | Content writer | Clinician with HRT background | **Clinician, blocking** |
| Reflection prompts | PM | Data — confirm each maps to a field (§3.1) | PM |

**Every claim in every lesson carries a citation and an evidence grade in the detail view**, per PRD §4.3.6. Unsourced precise numbers are cut, not softened.

**Three journeys are blocked on clinical review.** That is a hiring/contracting dependency for Phase 1, not a nice-to-have, and it should be started now — clinician availability, not writing, is the critical path.

---

## 9. Acceptance criteria

Launch-blocking:

- [ ] Every journey carries ≥6 distinct BCTs, none exceeding 40% of tagged days
- [ ] `current_index` advances on completion, never on calendar date (§4)
- [ ] No journey surface displays a "behind schedule" state or missed-day count
- [ ] Recovery break contains no journey-progress reference (§4.1)
- [ ] **Sleep Reset gate is unskippable and unreachable-around**; verified by attempting enrollment via every entry point including deep links
- [ ] **Sleep window algorithm cannot propose < 5.5 hours** — unit tested against adversarial diary data
- [ ] Sleepiness check on days 5/10/15 overrides titration and extends the window
- [ ] Titration pauses on ≥2 missing nights in trailing 5; never imputes
- [ ] Routed-out users are offered the stimulus-control variant, not a dead end
- [ ] Mood Activation contains no severity scoring and no treatment claim (D12)
- [ ] Unhook category picker excludes substances, alcohol, eating (D4)
- [ ] Journeys introduce ≤1 habit/day, ≤5 total
- [ ] Journey end does not retire its habits
- [ ] Three clinical sign-offs recorded before content ships

---

## 10. Open questions

1. **Is 28 days right for Sleep Reset?** Clinical dCBT-I typically runs 6–8 weeks. We compressed for consumer completion rates, which trades efficacy for adherence — a real trade and possibly the wrong one. The clinician review should rule on it, and if they say 6 weeks, we ship 6 weeks.
2. **Does completion-based advancement (§4) reduce or increase abandonment?** The argument for it is strong on user-need grounds and untested. Watch for the failure mode where a journey stretches so far that it loses coherence — someone on day 6 after two months has a different relationship to it than the design assumes.
3. **Five habits per journey — too many?** Engine §7 caps chains at 3 for the same reason. Five separate habits from one 28-day program may already be more than anyone sustains.
4. **Does the day 1–7 no-change baseline hold users?** It is right on the evidence (self-monitoring is active, and it earns the day-12 ask) and it is a week before the product visibly does anything. This is the highest-risk design choice in Sleep Reset and it should be qualitatively tested before launch, not after.
