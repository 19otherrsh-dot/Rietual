# Product Requirements Document — RITUAL

**Product Name:** RITUAL (working title)
**Category:** Behavioral science-based habit & wellness platform
**Version:** 1.2
**Date:** 8 August 2026
**Supersedes:** v1.0 (March 2025), v1.1 (7 August 2026)
**Amended by:** DECISIONS-v1 — D7, D8, D10, D11, D12, D13, D14 applied below

> **Note on carried-over data.** Market sizing, competitor download figures, and pricing benchmarks in §2 and §4.9 are inherited from v1.0 and were current as of March 2025. They must be refreshed before this document is used for fundraising or board approval. Behavioral science citations in §5 have been updated and evidence-graded.

---

## 0. Changelog: v1.0 → v1.1

This revision folds in an evidence review and corrects three specifications that were net-negative as written.

### Corrections (breaking changes to v1.0 direction)

| # | v1.0 / proposal | v1.1 decision | Reason |
|---|---|---|---|
| C1 | "Implementation intentions + mental imagery": users vividly imagine the positive feeling during and after execution | **Replaced with MCII / WOOP.** Obstacle imagery is mandatory; outcome imagery never ships alone | Positive fantasizing about a desired outcome *reduces* effort and attainment (Oettingen & Mayer 1990/2002; replicated in weight loss, job search, recovery). The proposed spec was the exact manipulation that backfires |
| C2 | "Dopamine scheduling": variable/randomized reward intensity on completion | **Variable *reward* schedules cut.** Variability moves to *informational* feedback (surfacing an unnoticed pattern). Reward fading retained | Variable-ratio reinforcement is the compulsion-loop mechanic; expected tangible rewards reliably undercut intrinsic motivation for the rewarded behavior (Deci, Koestner & Ryan 1999). Directly contradicts the identity architecture in §4.2.2 |
| C3 | "Nervous system regulation" framed via polyvagal theory | **Practices ship; the theory does not.** Copy references paced breathing, physiological sighs, and HRV. No ventral/dorsal vagal taxonomy in user-facing or marketing content | Polyvagal theory's core physiological claims are contested in peer review (Grossman & Taylor 2007; Grossman 2023). Slow paced breathing (~6 br/min) has independent support. Shipping the contested theory endangers the advisory-board credibility strategy |
| C4 | Motivation modeling grounded in willpower/ego depletion | **Depletion language removed from all coaching scripts.** Motivation-wave design retained on Fogg's behavior-model grounds only | Ego depletion failed large multi-lab replication (Hagger et al. 2016). The design advice survives; the mechanism story does not |
| C5 | Transtheoretical Model (TTM) stage-matched interventions as core personalization | **Replaced by HAPA** (Health Action Process Approach) as the primary volitional framework | Evidence for stage-matched interventions is weak; HAPA's motivational/volitional split is better supported and maps directly to buildable objects (action plan, coping plan, recovery self-efficacy) |
| C6 | Day-30 retention target of 25% | **Revised to 10% (target) / 18% (stretch)** | Benchmark for consumer mental-health apps is a median of ~3–4% DAU retention at day 30 (Baumel et al. 2019). 25% was 5–10× observed norms and would have mispriced the entire business model |
| C7 | "HIPAA-aligned" compliance posture | **Reframed to FTC HBNR + state consumer-health-data law + GDPR Art. 9** | HIPAA does not reach a direct-to-consumer wellness app absent covered-entity/BA status. Claiming compliance with an inapplicable regime is itself an FTC deception risk. See §6.2 |

### Additions (new to v1.1)

- **§4.4 The Failure Layer** — new headline section. Lapse-recovery protocol, coping plans, recovery self-efficacy, action-crisis detection. v1.0 treated lapse as an edge case; it is the modal user experience and the primary retention failure point.
- **§4.7 Quit Track** — v1.0 had no mechanism for *stopping* a behavior. Habit reversal + inhibitional implementation intentions.
- **§4.5.4 Supportive Accountability (human coach tier)** — highest-ROI addition in this revision. Human support is the strongest single moderator of digital intervention adherence.
- **§4.3.3 Cue-stability auditing** — diagnoses the most common structural cause of stack failure; no competitor ships it.
- **§4.6.1 Validated instrument battery** — SRBAI, BREQ-3, WHO-5, MCTQ, PSS-10. Replaces bespoke scales. *(v1.1 also listed PHQ-8 and GAD-7; both removed from Phase 1 by D12 — see §4.6.1.)*
- **§4.1.5 Fresh-start scheduling and §4.4.5 transition mode** — temporal landmarks and habit discontinuity windows.
- **§5 Behavioral Science Foundations** — mechanism→feature map with evidence grades, plus an explicit *rejected mechanisms* register.
- **§8.8 RITUAL Labs** now specifies **micro-randomized trials** as the method, not A/B tests.

---

## 1. Executive Summary

RITUAL is a behavioral-science-driven platform that closes the intention–action gap through structured habit formation, journey-based programs, and personalized coaching. It converts abstract wellness goals into context-cued routines that require progressively less deliberation.

**Core value proposition.** Generic habit trackers log behavior and rely on willpower. RITUAL engineers the conditions under which behavior repeats: stable cues, if-then plans that include the obstacle, protocols for what happens after a miss, and a human being who notices when you disappear.

**What differentiates v1.1 specifically.** Three claims, in priority order:

1. **We are built around failure, not success.** Every competitor optimizes the completed-habit path. Lapse is the modal experience, and it is where retention dies. §4.4 is our moat.
2. **Habits graduate.** A habit that still needs a notification is not a habit. We fade prompts on a schedule and measure unprompted completion as the primary success metric (§4.3.5). We are the only product with an incentive-aligned reason to make ourselves less necessary — and we monetize the next habit, not the last one.
3. **We use instruments that already exist.** SRBAI, BREQ-3, MCTQ, WHO-5. Validated measures gate our outcome claims, enable the research platform, and are the substance behind the "scientific transparency" positioning that 78% of privacy-wary uninstallers say they want.

---

## 2. Market Context & Opportunity

*(Figures inherited from v1.0; refresh before external use.)*

- Fabulous has reached 30M+ downloads; named Google's Best App for Self-Care
- Wellness app market projected at $281.2B by 2030
- 78% of users uninstall wellness apps over unclear data policies
- Recurring pain points in incumbents: confusing pricing, overwhelming UI, absent scientific transparency

### 2.1 Target users

| Segment | Characteristics | Needs | Primary v1.1 features |
|---|---|---|---|
| Wellness beginners | Overwhelmed by change, needs structure | Guided, small-step approach | Peripheral ELM track (§4.1.3), single-habit start |
| Neurodivergent users | ADHD, executive function challenges | Visual journeys, reduced decision fatigue | Cue-stability audit (§4.3.3), Quit Track (§4.7), reduced-notification mode |
| High achievers | Goal-oriented, data-driven | Progress tracking, optimization | N-of-1 experiments (§8.8), central ELM track, instrument battery |
| Burned-out professionals | Irregular schedules, stress | Flexible routines, stress management | Transition mode (§4.4.5), goal-conflict detection (§4.3.4), Quit Track |

**Segment note.** Half of the neurodivergent and burned-out segments arrive wanting to *stop* something — doomscrolling, late-night snacking, revenge bedtime procrastination. v1.0 had no product for them. §4.7 addresses this.

---

## 3. Product Principles

1. **Design for the miss.** Every flow has a defined behavior for the failure case, specified before the success case is built.
2. **The obstacle is part of the plan.** No planning UI ships without an obstacle field.
3. **Prompts are scaffolding, not product.** Anything we cue, we plan to stop cueing.
4. **Validated over bespoke.** If a measure exists in the literature, we use it rather than inventing a scale.
5. **Progressive disclosure.** Complexity appears only when the user is ready for it.
6. **Positive framing without dishonesty.** "5-day streak," not "2 days missed" — but never a fabricated win.
7. **We do not build compulsion loops.** Engagement mechanics that would be at home in a slot machine are out of scope regardless of their effect on DAU.

---

## 4. Core Features

### 4.1 Onboarding & Personalization Engine

**Objective:** Establish a behavioral baseline and produce immediate, defensible personalization.

#### 4.1.1 Intake assessment

Multi-question flow covering sleep, energy, focus, available time, and life domains (parenthood, finance, organization). Grounded in self-determination theory: the intake must produce a felt sense of autonomy and competence, not an audit.

**Instrumented at intake** (see §4.6.1 for full battery):
- **MCTQ** (Munich Chronotype Questionnaire, short form) — chronotype
- **BREQ-3** subset — motivation quality (autonomous vs. controlled)
- **WHO-5** — baseline wellbeing
- **ELM screener** — 3 items, see §4.1.3

#### 4.1.2 Goal selection & first plan (WOOP)

Users select a themed journey, then build their first plan using **WOOP / MCII** — the corrected replacement for v1.0's imagery spec (see C1):

1. **Wish** — what do you want from the next two weeks? (specific, feasible)
2. **Outcome** — imagine the best result. *Vivid, 15 seconds.*
3. **Obstacle** — imagine the **internal** obstacle that will actually stop you. *Vivid, 15 seconds. Mandatory field; cannot be skipped within this path.*
4. **Plan** — "If [obstacle], then I will [response]."

**Implementation constraints:**
- **Onboarding forks (D5): "set it up properly" runs the full WOOP; "quick setup" gives a plain if-then plan in 45 seconds, and WOOP is offered at that user's first lapse instead.** On day one the obstacle question is hypothetical and users guess; after a real miss they know. The escape hatch from the imagining is the fork, never a skip button inside WOOP — a WOOP with skipped timers is an if-then plan we would be mislabeling.
- The obstacle step is required. There is no skip. If the user cannot name one, offer a picker of common internal obstacles (tiredness, "I'll do it later," resentment, anxiety about starting) — external obstacles ("my kid was sick") route to coping planning (§4.4.2) instead, because they need a different response class.
- Outcome imagery is never presented as a standalone exercise anywhere in the product. It always appears in the four-step sequence.
- Guided-audio version: 90 seconds, all four steps. Not a "positive visualization" track.

#### 4.1.3 ELM cognitive-style routing

Three-item screener at intake classifies users onto one of two content tracks (Elaboration Likelihood Model):

| Track | User profile | Content form | Session length |
|---|---|---|---|
| **Central** | High motivation, wants the reasoning | Long-form education, mechanism explanations, citations, deep-dive coaching | 5–10 min |
| **Peripheral** | Low motivation or low available attention | Visual cues, one-tap actions, minimal text, immediate confirmation | <60 sec |

Dynamic reclassification: engagement decay on the central track auto-offers a peripheral switch. The switch is offered, never silently applied — silently simplifying someone's experience reads as condescension when they notice.

*Evidence grade: Moderate. ELM is well-established in persuasion research; its application to mHealth tailoring is supported by systematic review but with heterogeneous effect sizes.*

#### 4.1.4 Barrier identification & habit-specific self-efficacy calibration

Users specify obstacles (time, motivation, environment). Then, per habit, a confidence rating (0–10): *"How confident are you that you could do this on your worst day this week?"*

| Confidence | Support level |
|---|---|
| 0–3 | Scaffolded: tiny-habit version only, extra structure, mastery logging emphasized |
| 4–7 | Standard: full if-then planning |
| 8–10 | Autonomy-supported: user designs their own variation, minimal prompting |

Habit-*specific* self-efficacy — not general confidence — is what moderates implementation-intention effectiveness. The question must name the behavior.

*Evidence grade: Strong (Bandura; self-efficacy as moderator well-replicated).*

#### 4.1.5 Fresh-start scheduling

Detect upcoming **temporal landmarks** (Mondays, month starts, birthdays, new year, semester starts, and user-reported moves/job changes) and time journey-start prompts and re-engagement campaigns to them rather than to arbitrary drip intervals.

*Evidence grade: Strong (Dai, Milkman & Riis 2014, "The Fresh Start Effect"). Cheap to build; among the highest expected-value items in Phase 1.*

#### 4.1.6 Onboarding flow

1. Welcome narrative — the behavioral science approach, stated plainly
2. 5–7 question lifestyle assessment + instrument battery
3. ELM screener
4. Journey recommendation with visual preview
5. **First WOOP plan** for exactly ONE habit
6. Self-efficacy calibration on that habit
7. Subscription gate — after value demonstration, never before

---

### 4.2 Journey-Based Habit Architecture

**Objective:** Convert abstract goals into concrete, time-bound, identity-linked programs.

#### 4.2.1 Journey structure

- **Duration:** 7–30+ day themed programs
- **Format:** Visual path with character progression
- **Components:** Daily lessons, habit tasks, reflection prompts, audio coaching
- **Every journey is tagged** with its constituent BCTs (Behaviour Change Technique Taxonomy v1, Michie et al. 2013). This is a build requirement, not documentation: BCT tagging is what lets us audit coverage, run §8.8 experiments at the technique level, and answer "why does this journey work" with something other than vibes.

#### 4.2.2 Identity-based framing

Users craft "I am someone who…" statements tied to each habit domain. Avatar and journey language reflect adopted identities rather than tracked behaviors ("Welcome back, early riser" rather than "7-day streak").

**Identity congruence check:** flag conflicts between stated goals and self-concept or chronotype — e.g. a confirmed late chronotype (MCTQ) attempting a 5am routine. Offer the chronotype-adjusted version rather than letting them fail for eight weeks.

*Evidence grade: **Moderate, and lower than commonly claimed.** Identity-based framing has support in self-concept and self-affirmation research, and correlational evidence links behavioral identity to persistence. Widely circulated precise effect sizes for "identity-based vs. outcome-based habit framing" do not trace to a locatable RCT — **do not use a specific percentage in marketing copy without a citation the advisory board has verified.** Ship the feature; grade the claim honestly.*

**Dependency:** This feature is incompatible with variable reward schedules (see C2). Building both would train users to perform the behavior for the payout rather than as an expression of who they are.

#### 4.2.3 Core journey library (revised)

| Journey | Focus | Duration | Core protocol | Change from v1.0 |
|---|---|---|---|---|
| **Sleep Reset** (was *Morning Mastery*) | Sleep/circadian | 28 days | **dCBT-I**: sleep consolidation, stimulus control, constructive worry, hygiene last. MCTQ-adjusted timing. Morning light exposure | **Rebuilt.** v1.0's version was sleep hygiene only — the weakest CBT-I component. See §4.2.4 |
| Deep Work Protocol | Productivity/focus | 14 days | Distraction elimination, time blocking, environment design, temptation bundling | Adds inhibitional if-then plans |
| **Mood Activation** (was *Anxiety Reset*) | Mental health | 30 days | **Behavioral activation**: activity scheduling with mastery/pleasure ratings. Paced breathing. Cognitive reframing | **Rebuilt.** BA is a standalone evidenced treatment and is structurally identical to what we already build — activity scheduling plus ratings. Our mood tracker currently only logs; this makes the logging therapeutic |
| Energy Engineering | Physical vitality | 28 days | Movement snacks (VILPA-style short vigorous bouts), nutrition timing, circadian alignment | Unchanged; VILPA framing added |
| Confidence Building | Self-esteem | 21 days | Graded social exposure, self-affirmation, mastery logging | **Power posing removed** — the expansive-posture-to-hormone effect failed replication (Ranehill et al. 2015). Retained only as a self-report-of-felt-power exercise, which is the surviving finding |
| **Unhook** (new) | Behavior cessation | 21 days | Habit reversal + inhibitional implementation intentions | New. See §4.7 |

#### 4.2.4 dCBT-I safety gate (blocking requirement)

Sleep consolidation/restriction has genuine contraindications. The Sleep Reset journey **must not launch** without a screening gate that routes out and recommends professional consultation for: bipolar disorder or history of mania, seizure disorders, untreated OSA risk (STOP-BANG), occupational driving or heavy machinery operation, and pregnancy. Users who screen out receive a stimulus-control-and-light-only variant with no sleep-window compression.

*Evidence grade: Strong. dCBT-I is the strongest evidence base available to a consumer wellness app (SHUTi, Sleepio RCTs) — which is exactly why the safety gate is non-negotiable.*

#### 4.2.5 Gamification

- Visual progress path with milestone celebrations
- **Flexible streaks** (one miss per week does not break the streak)
- Unlockable content on journey completion
- Character evolution tied to identity statements (§4.2.2)

**Explicitly out of scope:** variable-ratio reward schedules, randomized celebration intensity, loss-framed streak-protection purchases, and any mechanic whose primary function is session-count inflation. Gamification evidence is mixed and skews short-term; where it conflicts with autonomy-supportive design (SDT), autonomy wins.

---

### 4.3 Routine Builder & Habit Stacking

**Objective:** Construct behavioral sequences that survive contact with a real week.

#### 4.3.1 Structure

- **Time blocks:** morning, afternoon, evening, custom
- **Habit stacking:** visual chain builder — "After [EXISTING HABIT], I will [NEW HABIT]"
- **Micro-habits:** 2-minute minimum viable version of every habit, defined at creation time (not improvised after a failure)
- **Contextual triggers:** time-, location-, or activity-based

**Templates:** The 5-Minute Morning (water → stretch → intention) · The Transition Ritual (work shutdown → movement → evening entry) · The Sleep Sequence (device shutdown → hygiene → reading → lights out)

#### 4.3.2 Temptation bundling

Users register their "wants" (specific podcasts, audiobooks, shows, playlists) and bind them to "shoulds":

- "Only listen to [series] while walking"
- "Only [show] on the treadmill"
- Screen Time / Digital Wellbeing API integration to enforce restricted access until completion

*Evidence grade: Moderate. Milkman, Minson & Volpp (2014) found meaningful gym-attendance gains, but the effect decayed over the study and most participants declined to pay for continued enforcement at the end. Ship it as an opt-in accelerant, not a core mechanic — and expect adherence to the bundle itself to erode.*

#### 4.3.3 Cue-stability audit *(new — competitive differentiator)*

Habit formation is context-dependent repetition. An unstable anchor is the most common structural reason a stack fails, and users cannot self-diagnose it — they read it as a personal failure of discipline.

Score each anchor cue for actual observed consistency:
- **Temporal variance** — spread of completion timestamps
- **Location variance** — coarse geo clustering (on-device where possible)
- **Calendar volatility** — variance of the surrounding calendar block

Surface it directly:

> *"Your 'after morning coffee' anchor happened between 6:40 and 11:15 this week. This cue is too unstable to build on yet. Two anchors in your week that ARE stable: [unlocking your laptop] · [the school run]."*

This reframes failure as a design problem, which is both accurate and the single most retention-protective message in the product.

**Placement (D11): at habit creation and re-planning only. Prohibited in the recovery break.** The same sentence is help before you commit and a verdict on your life afterwards — entirely a function of timing. Anchor stability is therefore surfaced when the user picks an anchor (ranking candidates by observed stability), never after three misses. Diagnosis at creation is worth more than diagnosis after failure anyway, and it costs one screen.

*Evidence grade: Strong on the underlying mechanism (context-dependent repetition; Lally et al. 2010 — median 66 days to plateau, range 18–254). The scoring implementation is novel and should be validated via §8.8.*

#### 4.3.4 Goal-conflict detection *(new)*

Most missed habits are multi-goal conflicts, not motivation failures. Cross-reference routine slots against the calendar and against each other; surface the collision explicitly and offer a reschedule before the miss happens rather than a guilt prompt after it.

#### 4.3.5 Reminder fading *(new — first-class scheduled behavior)*

Prompts reduce forgetting but create external-cue dependence. A habit that only fires on notification is not a habit; it is a compliance behavior with our notification.

- Reminders fade on a planned schedule as unprompted completions accumulate
- **Primary success metric is "completed without prompt,"** not "completed" (see §9.1)
- Occasional retrieval probes: *"What was your if-then plan for today?"* — spaced retrieval strengthens the intention's memory trace
- On a miss, the recovery message restates the user's **specific if-then plan**, never generic encouragement

#### 4.3.6 Science-backed tips

Contextual tips per habit, drawn from the environment-design literature. **Every tip must carry a source and an evidence grade in the tip detail view.** Tips citing effects we cannot trace (the v1.0 draft included "reduces friction by 40%") are cut, not softened — an unsourced precise number is worse than no number.

---

### 4.4 The Failure Layer *(new — headline section)*

**Objective:** Own the moment every competitor abandons.

Retention in this category does not die on the day someone stops caring. It dies on the day after their first miss. v1.0 addressed this with flexible streaks and pause clauses — necessary, insufficient, and entirely passive.

#### 4.4.1 Lapse-recovery protocol

The **abstinence violation effect** (Polivy & Herman's "what the hell" effect) means a single miss triggers disproportionate abandonment via self-blame → mood repair → further abandonment. The intervention with the best evidence is **self-compassion**, not encouragement: self-compassion after a failure increases subsequent self-improvement motivation, where self-esteem-boosting does not (Breines & Chen 2012; Sirois on self-compassion and health behavior).

**Spec — the 45-second recovery break, triggered on any miss:**

1. **Name it.** "That was a hard one." — acknowledge the difficulty without minimizing
2. **Common humanity.** "Most people miss this one in week two." — factual, drawn from our own cohort data, never fabricated
3. **Smallest next version.** "What's the two-minute version you'd do tomorrow?"
4. **Restate the plan.** Ends by re-committing the user's specific if-then plan

**Tone constraints (hard requirements):**
- Never shame-toned. Never cheerleading. Both increase abandonment — cheerleading because it signals the app has not understood what happened.
- No streak-loss dramatization. No broken-flame animation.
- The user's own words from their obstacle field (§4.1.2) may be quoted back. This is the single highest-signal personalization available and costs nothing.

*Evidence grade: Strong on the AVE; Moderate-to-strong on the self-compassion intervention.*

#### 4.4.2 Coping plans as a distinct object (HAPA)

Following HAPA (Schwarzer), planning splits into two objects that our data model must treat separately:

| Object | Content | Created |
|---|---|---|
| **Action plan** | *When, where, how* I will do it | At habit creation (§4.1.2) |
| **Coping plan** | *If [specific barrier], then [specific recovery]* | After the first miss, seeded by the actual barrier encountered |

Coping plans are generated from real failures, not hypothetical ones. The first miss is therefore a *feature-generating event*, and the product should treat it as such.

*Evidence grade: Strong (HAPA is well-supported; action + coping planning outperforms action planning alone).*

#### 4.4.3 Recovery self-efficacy

A distinct, separately measured construct: *"How confident are you that you'd restart this after missing three days?"* (0–10).

It predicts maintenance independently of task self-efficacy, it is cheap to collect, and **no consumer habit app models it.** Low recovery self-efficacy is the highest-priority trigger for human coach outreach (§4.5.4).

#### 4.4.4 Action-crisis detection

Brandstätter's **action crisis** is a validated construct: the phase in which someone is actively torn between pursuing and abandoning a goal. It *precedes* the behavioral dropoff and is measurable with a short scale.

This is a cheaper, more interpretable, and earlier signal than the LSTM-based failure prediction proposed in v1.0 §6.1 — and it can ship in Phase 1 rather than Phase 2. The ML approach remains on the roadmap as an augmentation, but the scale is the baseline it must beat.

#### 4.4.5 Transition mode (habit discontinuity windows)

Verplanken's habit discontinuity hypothesis: existing habits are disrupted — and therefore newly malleable — during life transitions.

Triggered by a move, new job, new baby, return from extended travel, or user declaration. In transition mode the app **rebuilds routines from scratch** rather than nagging about broken streaks, and pauses all streak accounting.

Combined with fresh-start scheduling (§4.1.5), this is our strongest retention moment: it is precisely when every other tracker loses the user, because every other tracker responds to a disrupted life by reporting a broken streak.

---

### 4.5 Coaching & Content

**Objective:** Just-in-time motivation, education, and — critically — a human being.

#### 4.5.1 Content types

| Type | Format | Use case |
|---|---|---|
| Daily coaching | 2–3 min audio | Morning motivation, habit rationale |
| Deep dives | 10–15 min | Behavioral science concepts (central ELM track) |
| SOS sessions | 5 min | Acute anxiety, motivation collapse, procrastination |
| Meditation / focus | Variable | Pre-work centering, sleep preparation |
| **Recovery breaks** | 45 sec | Post-lapse (§4.4.1) |

#### 4.5.2 Regulation protocols (corrected framing — see C3)

Ships: paced breathing at ~6 breaths/min, physiological sigh (double inhale, extended exhale), cold-water face immersion, humming/extended exhale work. Optional pre-habit arousal check (self-report or HRV where a wearable is connected), with a 60-second regulation step offered — **offered, not gated** — before demanding habits.

Does not ship: ventral/dorsal vagal taxonomy, "window of tolerance" as explanatory copy, polyvagal branding. Describe what the practice does (slows breathing, raises HRV, reduces self-reported arousal) rather than narrating a contested mechanism.

#### 4.5.3 ADHD track

Short concrete task breakdowns · "smallest possible action" prompts · reduced notification frequency · visual timers · body-doubling sessions (§4.8). Cue-stability auditing (§4.3.3) is disproportionately valuable for this segment, where variable routines are the norm rather than the exception.

#### 4.5.4 Supportive accountability — human coach tier *(new, highest priority)*

**This is the highest-ROI addition in v1.1 and it was absent from v1.0 entirely.**

Across digital mental health, human support is the strongest single moderator of adherence and effectiveness. Guided interventions substantially outperform unguided ones — consistently, across meta-analyses — even when the guide is a trained non-clinician spending a few minutes per user per week (Mohr's supportive accountability model, 2011).

v1.0's "accountability partnerships" (peer 1:1 matching) is the weakest form of this: unguided, untrained, and itself subject to attrition.

**Spec:**
- **Caseload cap: 150 users per coach (D13).** This number comes from a single requirement — a coach must be able to read a user's history before replying, and recall them without prompting. It is not derived from a margin target, and it must not be revised to hit one. The entire evidence base for supportive accountability rests on a person who *notices*; a coach at 400 users is a queue, and a user can tell within two exchanges. At that point we are charging for templated replies and the differentiator is gone. **Consequence: the tier may need to price above $39, or launch capped with a waitlist. Both beat launching it hollow.** Revisit only with evidence about quality at higher ratios.
- **Does not launch before the crisis protocol exists (D14).** Coaches *will* receive disclosures they are not qualified for — that is a certainty, not a risk. Putting a person in the path creates a duty, and a user who discloses something serious and receives a scripted deflection has been failed worse than one who never had a coach.
- Asynchronous, low-touch, high-leverage. Trained non-clinician coaches, not therapists. **Scope boundary is a hard requirement:** coaches do not diagnose, do not treat, and route per §11 crisis protocol.
- Weekly async check-in (text/voice note), ~5–8 minutes of coach time per user per week
- Coach queue is **prioritized by signal**, not round-robin: action-crisis flags (§4.4.4), low recovery self-efficacy (§4.4.3), and post-lapse non-recovery jump the queue
- Coaches see the user's obstacle field, coping plans, and completion pattern — not raw journal entries (privacy boundary, disclosed at signup)

**Margin note.** This is real COGS and it does not fit inside a $3.33/month annual plan. It is a distinct tier (§4.9), and it is priced as one. The strategic case: it is also the only feature on this list that a platform giant will not copy, because it does not scale to a billion users — which is precisely what makes it defensible.

---

### 4.6 Tracking, Measurement & Reflection

#### 4.6.1 Validated instrument battery *(new)*

Use instruments that exist. This costs nothing, gates outcome claims, makes §8.8 IRB-approvable, and is the actual substance behind the scientific-transparency positioning.

| Construct | Instrument | Cadence | Replaces |
|---|---|---|---|
| Habit automaticity | **SRBAI** (4-item Self-Report Behavioural Automaticity Index) | Biweekly per habit | v1.0's invented 1–7 "automaticity score" |
| Motivation quality | **BREQ-3** subset (autonomous vs. controlled) | Monthly | — |
| Wellbeing | **WHO-5** | Monthly | v1.0's composite "Wellness Index" |
| Chronotype | **MCTQ** (short) | Intake, annually | Proposed 23andMe CLOCK-gene partnership (§8.6) |
| Perceived stress | **PSS-10** | Monthly | — |
| ~~Depression~~ | ~~PHQ-8~~ | **Not in Phase 1** | D12 |
| ~~Anxiety~~ | ~~GAD-7~~ | **Not in Phase 1** | D12 |

**No depression or anxiety screening ships in Phase 1 (D12).** Not PHQ-9, not PHQ-8, not GAD-7, not opt-in, not behind a settings menu.

v1.1 reasoned that PHQ-8 sidesteps the item-9 crisis-response obligation. It does — but a user scoring 19 on a PHQ-8 is a user in trouble, and our plan was to record it and recommend a journey. **Screening we cannot act on serves the research platform, not the person answering the questions.** WHO-5 is a wellbeing measure, reads as one, and creates no duty we are not currently able to meet.

This is deliberately a weaker outcome claim: in Phase 1 we can say wellbeing improved, and we cannot say depressive symptoms did. That is the correct thing to be able to claim at this stage.

**Unblocked by this:** the crisis protocol is no longer a Phase 1 dependency. It becomes a Phase 2 prerequisite for the Guided tier only (§4.5.4, D14), where a human is in the path and escalation is real. PHQ-8/GAD-7 may be reconsidered at that point.

**MCTQ note:** chronotype assessment delivers most of what the proposed genetic-testing partnership promised (§8.6), at zero partnership cost, with better validity and no genetic-data liability.

#### 4.6.2 Daily tracking

- **Habit completion** — binary, with prompted/unprompted distinction (§4.3.5)
- **Mood** — 5-point with emotion tags (energy, focus, stress); on the Mood Activation journey this becomes BA-style **mastery and pleasure** ratings
- **Sleep** — duration, quality, consistency (HealthKit/Google Fit import where available)
- **Water / gratitude** — quick-log counters
- **Journal** — free-form with prompts

**Self-monitoring is itself an active ingredient**, not just instrumentation: monitoring goal progress improves attainment, with larger effects when recording is physical or public (Harkin et al. 2016 meta-analysis). This justifies tracking as a *feature* rather than as data collection, and it is the honest answer to "why should I log this."

#### 4.6.3 Correlation insights

*"On days you complete your morning routine, your average focus rating is 23% higher."*

**Constraint:** these are within-person correlations from observational self-report and must be labeled as such. Causal phrasing ("your morning routine raises your focus by 23%") is prohibited in the copy deck. Users who want causal answers get N-of-1 experiments (§8.8) — which is a better product anyway.

#### 4.6.4 Habit graduation

When SRBAI plateaus above threshold, the habit **graduates**: it leaves active tracking, reminders stop entirely, and it moves to a periodic maintenance check. Kwasnicka et al.'s (2016) framework of behavior maintenance treats sustained habit, resources, and environment as distinct from initiation motives — the product should reflect that a maintained habit needs a different relationship than a forming one.

No competitor lets a habit leave the tracker. Ours does, and we say so in marketing.

**Not negotiable (D10).** Whatever graduation costs in subscription months, the alternative is a product with a structural interest in the user never succeeding — which would quietly falsify every other claim in this document.

---

### 4.7 Quit Track — behavior cessation *(new)*

**Objective:** Serve the half of our target segments who arrive wanting to stop something.

v1.0 could only add behaviors. Doomscrolling, late-night snacking, revenge bedtime procrastination, and nail-biting have no home in an add-a-habit model.

**Protocol — habit reversal training** (strong RCT base in tics and body-focused repetitive behaviors, widely adapted):

1. **Awareness training** — log occurrences and the antecedent; most users cannot initially name their cue
2. **Cue identification** — same stability scoring as §4.3.3, applied in reverse
3. **Competing response** — a physically incompatible action, held ~1 minute (hands occupied, phone in another room, tongue to roof of mouth)
4. **Social support** — a named person who knows, ideally a coach (§4.5.4)

**Plus inhibitional implementation intentions:** "If I see [cue], then I will ignore it." Distraction- and temptation-inhibiting if-then plans are a distinct and effective class within the implementation-intention literature (Gollwitzer & Sheeran 2006 meta-analysis: d ≈ 0.65 overall across 94 studies).

**Environment design first.** For most digital-behavior quits, stimulus control (app removed from phone, charger in another room, grayscale) outperforms every willpower-based technique, and we should say so even though it means the user opens our app less.

**Phase 1 scope (D4): digital and behavioral targets only** — scrolling, phone in the bedroom, late-night snacking as habit. Substances, alcohol, and anything adjacent to disordered eating are **excluded from the category picker entirely**, not permitted with a warning. Lapse in a clinically loaded cessation category can do real harm, and our recovery copy was written by analogy from missed walks. A user in recovery deserves either a product built for that or no product at all; a warning is not a substitute for not shipping it. Unblocks with clinical review in Phase 2.

---

### 4.8 Community & Social (Circles)

- **Themed circles** — journey-specific cohorts ("Sleep Reset · September")
- **Challenge events** — time-bound collective goals
- **Anonymous sharing** — progress without identity
- **Body doubling** — virtual co-working with real-time routine completion; disproportionately valuable for the ADHD track
- **Accountability partnerships** — retained, but positioned as complementary to §4.5.4, not a substitute

**Normative feedback — with the correction.** Descriptive norms ("72% of users like you complete this on Mondays") **backfire for above-average performers**, dragging them down toward the mean (the boomerang effect; Schultz et al. 2007). Any descriptive norm shown to a user performing above it must be paired with an injunctive signal (approval of their current behavior). This is a one-line rule that most products get wrong.

**Commitment contracts** (public stakes, charity forfeits) are retained as an opt-in Phase 3 feature with caveats: they help completers but reduce sign-up, and stake escalation on missed days risks compounding exactly the shame spiral §4.4.1 exists to prevent. Escalating stakes as proposed in v1.0 are **cut**; flat stakes with pause clauses only.

---

### 4.9 Monetization

| Tier | Price | Features |
|---|---|---|
| Free | $0 | One morning routine, 3 habits, basic tracking, limited journeys, **and the complete failure layer — permanently** (D8) |
| Premium Monthly | $16.99/mo | Unlimited routines, all journeys, full coaching library, community, full instrument battery |
| Premium Annual | $39.99/yr (~$3.33/mo) | Same as monthly |
| **Guided** *(new)* | **$29–39/mo** | Premium + human coach (§4.5.4), priority queue on failure signals |
| Lifetime | $149.99 | All current and future *content*; excludes Guided (human COGS cannot be prepaid) |

**Pricing psychology:** anchor annual against a monthly coffee · plain feature-comparison table (explicitly avoiding the confusing-bundle problem users report with incumbents).

**Paywall placement (D7): day 7, flat.** No completion requirement, no behavioral gating, no variation by usage. A completion-gated paywall asks the people it is working for to pay while letting the people it is not working for drift away — which inverts who we should be charging. A week is long enough for anyone to know, and a fixed date is predictable enough to state plainly at signup instead of springing on them. *Cost: slower conversion than gating at three completions, plus some carried users who were never going to pay. Accepted.*

**The failure layer is free forever (D8)** — recovery breaks, coping plans, skip, and pause, at every tier, **including after a paid plan is cancelled.** Nobody converts on a feature they have not yet needed. Three completions is a commodity experience; a lapse met well is the only thing here nobody else does, and gating it means the user meets our differentiator as a locked door at the exact moment they are deciding whether we are worth paying for. The harder half: a user who cancels is frequently a user who is struggling, and withdrawing lapse support at that moment would be the most cynical thing in this product. *Cost: our most expensive feature is our free one. Paid is breadth, depth, and people. Accepted.*

**Structural note.** The Guided tier is the only tier with variable cost, and it is the only tier a platform incumbent cannot trivially replicate. Model it separately; do not let it be averaged into blended margin.

---

## 5. Behavioral Science Foundations

### 5.1 Mechanism → feature map

| Mechanism | Evidence | Feature |
|---|---|---|
| Implementation intentions | **Strong** — Gollwitzer & Sheeran 2006, d ≈ 0.65, 94 studies | §4.1.2, §4.7 |
| Mental contrasting (MCII/WOOP) | **Strong** — Oettingen; contrasting outperforms indulging or dwelling | §4.1.2 |
| Context-dependent repetition | **Strong** — Lally et al. 2010, median 66 days (range 18–254) | §4.3.3, §4.6.4 |
| Abstinence violation effect | **Strong** — Polivy & Herman | §4.4.1 |
| Self-compassion after failure | **Moderate–strong** — Breines & Chen 2012; Sirois | §4.4.1 |
| HAPA action/coping planning | **Strong** — Schwarzer, Sniehotta | §4.4.2 |
| Recovery self-efficacy | **Moderate–strong** | §4.4.3 |
| Action crisis | **Moderate** — Brandstätter; validated scale | §4.4.4 |
| Habit discontinuity | **Moderate** — Verplanken | §4.4.5 |
| Fresh start effect | **Strong** — Dai, Milkman & Riis 2014 | §4.1.5 |
| Supportive accountability | **Strong** — Mohr 2011; guided > unguided across meta-analyses | §4.5.4 |
| Self-monitoring reactivity | **Strong** — Harkin et al. 2016 | §4.6.2 |
| dCBT-I | **Strong** — SHUTi, Sleepio RCTs | §4.2.3 |
| Behavioral activation | **Strong** — standalone evidenced treatment | §4.2.3 |
| Habit reversal training | **Strong** in tics/BFRBs; adapted elsewhere | §4.7 |
| Self-determination theory | **Strong** | Throughout; §4.2.5 constraint |
| Temptation bundling | **Moderate** — Milkman et al. 2014; effect decayed | §4.3.2 |
| ELM tailoring | **Moderate** — heterogeneous in mHealth | §4.1.3 |
| Episodic future thinking | **Moderate** — reduces delay discounting | §8.2 |
| Identity-based framing | **Moderate; commonly overstated** | §4.2.2 |
| Descriptive norms | **Strong, with boomerang risk** — Schultz et al. 2007 | §4.8 |
| Commitment contracts | **Moderate; selection effects** | §4.8 |

### 5.2 Rejected mechanisms register

Kept deliberately, and kept public. This register is a differentiator: it is the concrete proof behind "we test what we preach," and it is what an advisory board is for.

| Mechanism | Status | Why |
|---|---|---|
| Ego depletion / willpower as fuel | **Rejected** | Failed multi-lab replication (Hagger et al. 2016) |
| Power posing (hormonal claims) | **Rejected** | Ranehill et al. 2015; only felt-power self-report survived |
| Polyvagal theory (as explanation) | **Rejected as framing** | Contested physiology (Grossman & Taylor 2007; Grossman 2023). Practices retained |
| Variable-ratio reward schedules | **Rejected on ethics + conflict** | Compulsion mechanic; undermines identity architecture and intrinsic motivation |
| Positive outcome fantasizing (alone) | **Rejected** | Reduces effort and attainment (Oettingen & Mayer) |
| TTM stage-matched interventions | **Rejected as core** | Weak evidence for stage-matching; HAPA substituted |
| Learning styles | **Rejected** | No evidential support; ELM is not this and must not be marketed as this |
| Genetic chronotype personalization | **Deferred** | MCTQ delivers the outcome now, cheaper, without genetic-data liability |

---

## 6. Technical Requirements

### 6.1 Platform & performance

- Native iOS & Android (not cross-platform — animation fidelity and background-scheduling reliability)
- **Offline mode** — core logging, journey content, and recovery breaks work without connectivity
- **Sync** — real-time across devices
- **Accessibility** — WCAG 2.1 AA, screen reader support, dyslexia-friendly font option, **reduced-motion toggle** (required for the ADHD/neurodivergent segments, not optional polish)

### 6.2 Data & privacy — corrected regulatory posture (see C7)

**HIPAA does not apply to us** as a direct-to-consumer wellness app absent covered-entity or business-associate status. v1.0's "HIPAA-aligned" claim is removed. Asserting compliance with an inapplicable regime is itself an FTC deception exposure.

The regimes that actually bind us:

| Regime | Applies to | Implication |
|---|---|---|
| **FTC Health Breach Notification Rule** (amended 2024) | Health apps handling identifiable health data | Breach notification duties; "breach" includes unauthorized *disclosure*, not just intrusion — third-party SDK data leakage counts |
| **Washington My Health My Data Act** | Broad "consumer health data" | Consent, separate authorization for sale, **private right of action** — the highest-risk US statute for us |
| **Nevada SB 370** | Consumer health data | Similar posture, no private right of action |
| **GDPR Art. 9** | EU special-category data | Explicit consent; health data processing basis |
| **CCPA/CPRA** | California | Sensitive personal information handling |
| FDA | If we make disease-treatment claims | §8.10 clinical integrations **change this analysis materially** — legal review required before Phase 3, not during |
| FTC health-claims substantiation | All outcome claims | Every efficacy claim needs competent and reliable scientific evidence. §5 grading is the internal control for this |

**Commitments:** encrypted at rest and in transit · clear data-usage dashboard · one-tap export and delete · **no sale of health data, ever, stated in the contract not just the marketing** · on-device processing wherever feasible (notably the geo component of cue-stability scoring, §4.3.3).

**Third-party SDK audit is a launch blocker.** The most common route to an HBNR violation in this category is an analytics or ad SDK exfiltrating health-adjacent events. Inventory every SDK's data egress before launch.

### 6.3 Integrations

- **HealthKit / Google Fit** — sleep, steps, heart rate, HRV
- **Calendar** — routine time blocking; also the data source for goal-conflict detection (§4.3.4)
- **Screen Time / Digital Wellbeing** — temptation bundling enforcement (§4.3.2), Quit Track stimulus control (§4.7)
- **Wearables** — Apple Watch, Garmin, Fitbit, Oura, Whoop quick-actions and HRV
- **Smart home** — Philips Hue (wake lighting, circadian), smart speakers (audio coaching)

---

## 7. Design Principles

### 7.1 Visual language

**Aesthetic:** "Warm Science" — credible but approachable.

**Color psychology:** mornings warm orange/yellow (energy) · afternoons cool blue (focus) · evenings deep purple (wind-down). *Note: chromatic mood effects are weakly evidenced; this is a design-coherence decision, not a behavioral intervention, and should not be marketed as one.*

**Animation:** purposeful micro-interactions (completion celebration), never ambient background motion. Full reduced-motion mode.

### 7.2 UX tenets

1. **Progressive disclosure** — complexity when ready
2. **Default to success** — pre-populate reasonable defaults
3. **Friction reduction** — max 3 taps to log any habit
4. **Positive framing** — "5-day streak," not "2 days missed"
5. **Design for the miss** *(new)* — every flow specifies its failure-case behavior before its success case
6. **No dark patterns** *(new)* — no fake urgency, no streak-anxiety monetization, no obstructed cancellation. Cancellation is as easy as signup, in every jurisdiction, regardless of local requirement

---

## 8. Innovation Pipeline

Retained from v1.0 §6 with revisions.

### 8.1 AI behavioral intelligence
Failure prediction (LSTM on temporal behavioral data), adaptive difficulty (RL with satisfaction reward), contextual coaching (contextual bandits), voice-first onboarding.

**Revision:** the **action-crisis scale (§4.4.4) is the Phase-1 baseline any model must beat.** A validated 6-item scale that ships now, is interpretable, and can be explained to a user is a better product than an unexplainable model that ships in month 11. Build the model to augment the scale, not to replace it.

Architect all just-in-time features as formal **JITAIs** (Nahum-Shani et al.): explicit decision points, tailoring variables, intervention options, and — the component most implementations omit — a **receptivity** model. Sending a perfectly-targeted intervention to someone who cannot act on it right now is worse than silence.

### 8.2 Episodic future thinking
**Revised.** v1.0/proposal called for AI-generated aging progressions of the user's face. The validated manipulation is **cue-generated vivid future event descriptions, authored by the user and replayed at decision points** — cheaper, better supported, and without the deepfake-of-the-user consent problem. Ship that version.

### 8.3 Biometric closed loop
HRV-guided intensity (low morning HRV → gentle routine variant) · sleep-stage-aware wake routines · CGM correlation for users with devices · stress-spike detection → SOS breathing.

**Caveat:** consumer HRV is noisy and highly individual. Ship as within-person relative-to-baseline signals with wide confidence bands, never as absolute readiness scores presented with false precision.

### 8.4 Social accountability 2.0
Body doubling · habit sponsorship · Slack/Teams integration. Promise protocols retained with flat (non-escalating) stakes only — see §4.8.

### 8.5 Environmental design marketplace
"Friction Reduction Store" — curated products mapped to stimulus control, implementation intentions, temptation removal, default bias.

**Requirement:** affiliate relationships must be disclosed inline at the recommendation, not in a footer. A commerce incentive inside a product whose credibility rests on scientific honesty is the single fastest way to lose the positioning; the mitigation is aggressive disclosure, not subtlety.

### 8.6 Precision wellness
**Deprioritized.** MCTQ chronotype (§4.6.1) captures most of the near-term value. Genetic and microbiome personalization for behavior change is currently **weak-to-emerging** evidence, adds significant data liability, and would be our most overclaimed feature. Revisit when the evidence base supports it.

### 8.7 AR habit anchors
Spatial cue placement, immersive journey visualization, AR body scan. Genuinely interesting as *cue placement in physical space* — which is mechanistically aligned with §4.3.3. Phase 3 exploration.

### 8.8 RITUAL Labs — research platform

**Method revision.** v1.0 specified A/B testing. The correct method for time-varying, in-the-moment interventions is the **micro-randomized trial** (Klasnja, Nahum-Shani et al.; HeartSteps is the canonical implementation). MRTs randomize at each decision point and answer the causal question we actually want to make claims about: *does this intervention work, at this moment, for this person's state?*

- Opt-in participation, IRB approval, academic partnership
- BCT-level tagging (§4.2.1) makes technique-level experimentation possible
- **N-of-1 / single-case experiments** exposed to users directly — ABAB designs on their own habits. Ideal for the high-achiever segment and the honest answer to §4.6.3's correlational limits
- Users get their own behavioral profile; findings become content

### 8.9 Family & intergenerational
Household dashboard · parent-child journeys · co-parenting coordination · elder-care medication adherence.

### 8.10 Clinical integration
Therapist dashboards, prescribed journeys, crisis detection, HSA/FSA eligibility, condition-specific programs.

**Gate:** this is the point at which we may become a regulated device and/or a HIPAA business associate. Nothing in §8.10 proceeds without prior legal and regulatory review. It is not a Phase 3 feature; it is a Phase 3 *decision*.

---

## 9. Success Metrics & KPIs

### 9.1 Engagement (revised — see C6)

| Metric | v1.0 target | **v1.1 target** | Stretch | Note |
|---|---|---|---|---|
| Day 7 retention | 40% | **22%** | 35% | |
| Day 30 retention | 25% | **10%** | 18% | Category median is ~3–4% DAU at D30 (Baumel et al. 2019); best-in-class subscription wellness reaches low teens |
| Day 90 retention | — | **6%** | 11% | New — D90 is the metric that actually predicts LTV |
| Monthly active habits | 12+ | **4+** | 8 | 12 was implausible and would indicate tracker-maximalism, not habit formation |
| Session frequency | 5+/wk | **4+/wk** | | Declining sessions on a graduated habit is a *success*, not churn — segment accordingly |

**Model the business against the v1.1 targets.** v1.0's numbers, if used for LTV projections, would have overstated lifetime value by roughly an order of magnitude at D30.

### 9.2 Behavioral outcomes (now instrument-backed)

| Outcome | Measure |
|---|---|
| **Primary: unprompted completion rate** | % completions with no notification in the preceding 2h (§4.3.5) |
| Habit automaticity | **SRBAI** trajectory (§4.6.1) |
| **Lapse recovery rate** | % of users completing the same habit within 72h of a miss — *our headline differentiating metric* |
| Motivation quality | BREQ-3 autonomous/controlled ratio, tracked over time |
| Wellbeing | WHO-5 change from baseline |
| Journey completion | % completing intended journeys |
| Graduation rate | Habits reaching SRBAI plateau and exiting tracking (§4.6.4) |

**Lapse recovery rate is the metric this product is organized around.** If §4.4 works, it moves; if it doesn't move, §4.4 is theater.

### 9.3 Business

- LTV:CAC > 3:1 · annual churn < 45% (revised from 30%, consistent with C6) · NPS > 50 · free-to-paid conversion > 5% (revised from 8%) · Guided-tier attach rate > 8% of paid

---

## 10. Roadmap

### Phase 1 — Foundation & the Failure Layer (Months 1–6)
- Core journey library (5 programs, including rebuilt Sleep Reset with §4.2.4 safety gate, and Mood Activation)
- Routine builder with habit stacking + **cue-stability audit**
- **WOOP onboarding** (§4.1.2)
- **The full Failure Layer** (§4.4) — recovery protocol, coping plans, recovery self-efficacy, action-crisis scale
- **Validated instrument battery** (§4.6.1) — WHO-5, MCTQ, SRBAI, BREQ-3, PSS-10. **No PHQ-8/GAD-7** (D12)
- **Fresh-start scheduling** (§4.1.5)
- Reminder fading + unprompted-completion metric
- iOS/Android parity; premium subscription launch
- Third-party SDK data-egress audit (launch blocker)

*Rationale for the reordering: §4.4 was Phase-3-shaped in v1.0 and is Phase 1 here. It is the differentiator, and it is also the thing that makes the Phase-1 retention numbers achievable at all.*

### Phase 2 — Human & Intelligence (Months 7–12)
- **Crisis protocol** — now a Phase 2 item and a hard prerequisite for everything below it (D12, D14). Detection thresholds, 24/7 routing, regional crisis-line data, coach escalation training, documented liability review
- **Guided tier / human coach** (§4.5.4) — manual, unscaled pilot of 150 users (one coach's full caseload, D13) before any tooling is built. Gated on the crisis protocol above
- Quit Track (§4.7)
- Biometric integrations (HealthKit, wearables, HRV)
- Circles + body doubling
- Habit graduation (§4.6.4)
- Temptation bundling with Screen Time integration
- AI coaching, benchmarked against the action-crisis baseline
- Enterprise beta

### Phase 3 — Ecosystem (Months 13–18)
- RITUAL Labs with MRT infrastructure + IRB
- Transition mode at scale; commitment contracts (flat stakes)
- Environment marketplace with inline disclosure
- AR exploration
- Clinical integration **decision gate** (§8.10) — regulatory review first
- International expansion with localized journeys

---

## 11. Risk Assessment

| Risk | Mitigation |
|---|---|
| **Scientific overclaiming** | §5 evidence grades are internal law. Every user-facing efficacy number carries a traceable citation or is cut. §5.2 rejected register published. Advisory board reviews the copy deck, not just the features |
| **Regulatory (privacy)** | §6.2 posture. WA MHMD private right of action is the top exposure. SDK egress audit before launch |
| **Regulatory (claims/device)** | FTC substantiation for all outcome claims. §8.10 gated behind counsel |
| **Clinical safety — sleep** | §4.2.4 contraindication screening is a blocking requirement for Sleep Reset |
| **Clinical safety — mental health** | **No depression/anxiety screening in Phase 1 at all (D12).** WHO-5 only. Crisis protocol is a Phase 2 prerequisite for the Guided tier (D14), not a Phase 1 blocker. Reconsider PHQ-8/GAD-7 only once a human is in the path and escalation is real |
| **Clinical safety — cessation** | Quit Track (§4.7) ships for digital/behavioral targets only in Phase 1 (D4). Substances, alcohol, and anything adjacent to disordered eating are excluded from the category picker — not warned about, excluded. Our recovery copy was written by analogy from missed walks |
| **Coach tier scope creep** | Coaches are not therapists. Written scope, training, escalation script, and audit. This is the largest liability surface in the Guided tier |
| **Notification fatigue** | Reminder fading (§4.3.5) makes reduced notification the designed end state, not a setting |
| **Shame spiral / harm from failure** | §4.4.1 tone constraints. Escalating stakes cut. This is a real harm vector in this category and it is under-discussed |
| **Marketplace credibility conflict** | Inline affiliate disclosure (§8.5) |
| **Guided-tier margin** | Modeled separately; not blended. Pilot manually before scaling |
| **Competition from Apple/Google** | Differentiation via the failure layer, human support, and community — none of which scale to a billion users, which is exactly the point |
| **Equity** | Interventions demanding high self-regulation widen outcome gaps. Peripheral ELM track and coach prioritization are partial mitigations; measure outcome variance by segment, not just means |
| **Retention shortfall** | v1.1 targets are benchmark-grounded (C6). If D30 lands below 8%, the Guided tier moves forward, not back |

---

## 12. Open Questions — resolved

All five v1.1 questions are closed in DECISIONS-v1. Retained here with their answers so the reasoning is not lost.

| v1.1 question | Resolution |
|---|---|
| 1. Coach unit economics | **Closed — D13.** 150:1, capped by whether a coach can remember you, not by margin. Price the tier to fit the caseload |
| 2. Does the recovery protocol move lapse recovery rate? | **Still open, and correctly so** — this is an empirical question, not a decision. Holdout configured; answers itself by month three. See §H below |
| 3. Does cue-stability feedback help or demoralize? | **Closed — D11.** Both, depending entirely on timing. Ships at habit creation and re-planning; **prohibited in the recovery break.** Told early it is help with a design problem; told after three misses it is a verdict on your life |
| 4. Graduation vs. revenue | **Closed — D10.** Graduate. Not negotiable. The alternative is a product with a structural interest in the user never succeeding |
| 5. Free-tier depth | **Closed — D8.** Free forever, including after cancellation. See §4.9 |

### 12.1 Genuinely still open

1. **Does the recovery protocol move lapse recovery rate?** The spine of this document rests on it. Not a decision to take — a result to wait for, and the reason §4.4 ships first is so we learn early rather than late.
2. **Quit Track clinical categories.** Blocked pending clinical review (D4), not undecided.

## 13. Immediate Next Steps

1. Advisory board review of §5.1 and §5.2 — the evidence grades gate the copy deck
2. Legal review of §6.2 posture, with priority on WA MHMD and the FTC HBNR SDK exposure
3. Qualitative testing of the §4.4.1 recovery-break script — tone is the entire feature
4. Design the §4.5.4 coach pilot as a manual, unscaled service — 150 users, one coach's full caseload (D13), no tooling
5. Refresh all §2 market data
6. Scope the §4.2.4 sleep contraindication screener with a clinical reviewer
7. IRB pre-consultation for §8.8 (long lead time; start in Phase 1)
