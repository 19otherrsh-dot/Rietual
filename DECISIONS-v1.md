# Decisions Register — Resolved from User Need

**Closes:** PRD v1.1 §12 · Failure Layer §13 · Onboarding §12 · Stack §12
**Version:** 1.0
**Date:** 7 August 2026

**Decision rule applied:** where an open question had a user-serving answer and a business-serving answer, the user-serving answer wins and the business consequence is stated rather than hidden. Nineteen questions were open across four documents. All nineteen are closed below. Six of them changed the specs.

Three decisions cost us money on purpose: **D7** (paywall at day 7), **D8** (failure layer free forever), **D15** (coach caseload capped by memory, not margin). Those are flagged.

---

## A. Failure layer

### D1 — One miss gets silence. *(Changes the spec)*

**Closes:** Failure Layer §13.3
**Decision:** No recovery break at `lapsed_1`. The first recovery break fires at `lapsed_2` — the second consecutive miss.

**Why:** After one miss most people have not registered a failure. Intervening tells them one occurred. A user who forgot to stretch on Tuesday needs Wednesday to arrive normally; they do not need a product noticing. We were about to manufacture the exact event the feature exists to soften.

**The exception that keeps it warm:** if the user *opens the app themselves* after a miss, show the light acknowledgment. They came looking — that's a pull, and pulls get answered. The rule is: **we never raise it first at one miss; we always answer it if they do.**

**Changes:** Failure Layer §2.1 state machine keeps `lapsed_1` as a state (it drives skip-annotation capture and the recovery metric) but removes its push-side trigger. §3.1 delivery rules gain the pull/push distinction. The MRT in §11.2 loses its `lapsed_1` arms and gains an arm at `lapsed_2`.

**Reverses if:** users who receive nothing at one miss show materially worse day-30 survival than a held-out group that got the light version.

---

### D2 — Shrinking is a week, not a demotion.

**Closes:** Failure Layer §13.2
**Decision:** The shrink offer at `lapsed_2` is time-boxed to 7 days, then auto-prompts to restore. It is called "the small version, for a week."

**Why:** A user came for an outcome, not for a streak. Permanently shrinking a 30-minute walk to 2 minutes protects our retention number while quietly abandoning the thing they wanted. Time-boxing gives them persistence through a bad week without losing the goal — and restoring on schedule is a competence experience rather than a concession.

**Changes:** Failure Layer §4.4 copy. Restore prompt added at day 7.

---

### D3 — 72 hours stays, as a metric only.

**Closes:** Failure Layer §13.1
**Decision:** Keep 72h as the definition of recovery for measurement. Decouple it entirely from intervention timing, which is now governed by D1.

**Why:** It spans a weekend, which is the shape of most real lapses. Nothing the user experiences depends on it, so it needs to be defensible rather than optimal.

---

### D4 — Quit Track ships for behavioral targets only. *(Changes scope)*

**Closes:** Failure Layer §13.4
**Decision:** Phase 1 Quit Track covers digital and behavioral targets — scrolling, phone in the bedroom, late-night snacking as habit. It does **not** cover substances, alcohol, or anything adjacent to disordered eating. Those categories are blocked until clinical review, and the category picker excludes them rather than warning about them.

**Why:** Lapse in a clinically loaded cessation category can do real harm, and our recovery copy was written by analogy from missed walks. A user in recovery deserves either a product built for that or no product at all. Warning them isn't a substitute for not shipping it.

**Cost:** narrower launch. Correct trade.

---

## B. Onboarding

### D5 — Two setup paths, and WOOP moves to where it's needed. *(Changes the spec — the biggest change here)*

**Closes:** Onboarding §12.1
**Decision:** Offer two paths at the first-plan step:

- **Quick setup (~45s)** — anchor, habit, plain if-then. No mental contrasting, no timers.
- **Set it up properly (~3 min)** — full WOOP with both 15-second imaginings (reduced from 20).

Quick-setup users are offered WOOP **at their first lapse**, not before.

**Why:** The imagining timers are the mechanism, so a WOOP with skipped timers is an if-then plan we're mislabeling. The honest options were "force the timers" or "offer a real fast path." Forcing is worse for the user; a degraded WOOP is worse for everyone.

And WOOP lands better at first lapse anyway. On day one, the obstacle question is hypothetical and users guess. After a real miss, they *know* what stopped them — the drill-down writes itself. We were asking the hardest question at the moment the user had the least to answer it with.

**Changes:** Onboarding §2 flow forks at screen 7. §3.1 rule 1 (all four steps or none) now applies within the proper path. Plans store `plan_type = woop | if_then`. Failure Layer §4.2 gains a WOOP-offer branch for `if_then` plans.

**Note:** this makes the first onboarding experiment (Onboarding §9.1) cleaner, not messier — arm B is now a shipping path rather than a synthetic condition.

---

### D6 — The obstacle gets a sentence.

**Closes:** Onboarding §12.2
**Decision:** No word limit. Guidance reads "a few words is enough." Stored verbatim, as already required.

**Why:** The protocol's keyword format serves recall. Our use is quotation — we read it back to someone at the worst moment of their week. Their sentence does that; our truncation of their sentence doesn't. Where the protocol and the user's voice conflict here, the voice wins, because the mechanism we're actually relying on at that moment is being understood.

---

### D7 — Paywall at day 7. Nothing else gates it. *(Costs money)*

**Closes:** Onboarding §12.4
**Decision:** Day 7, flat. No completion requirement, no "third completion or day 5," no variation by behavior.

**Why:** A completion-gated paywall punishes exactly the users who are struggling — it asks the people it's working for to pay and lets the people it isn't working for drift. A week is long enough for anyone to know, and it's predictable, which means we can state it plainly at signup instead of surprising them.

**Cost:** slower conversion than gating at three completions, and we'll carry some users who were never going to pay. Accepted.

---

### D8 — The failure layer is free, permanently. *(Costs money)*

**Closes:** PRD §12.5 and Onboarding §12.5
**Decision:** Recovery breaks, coping plans, skip, and pause are free forever, at any tier, including after cancellation of a paid plan.

**Why:** Nobody converts on a feature they haven't needed yet. Three completions is a commodity experience; a lapse met well is the only thing here that nobody else does. Putting it behind the gate means the user meets our differentiator at the exact moment they're deciding whether we're worth paying for — and meets it as a locked door.

The harder half: a user who cancels is often a user who is struggling. Taking away the lapse support at that moment would be the single most cynical thing in the product.

**Cost:** our most expensive feature is our free one. Paid becomes breadth (habits, journeys, audio), depth (full instrument battery, insights), and people (Guided). Accepted.

---

### D9 — Keep the internal/external drill-down, once, in the proper path only.

**Closes:** Onboarding §12.3
**Decision:** Retained in the WOOP path. Not present in quick setup. Maximum one drill-down, then accept whatever they gave.

**Why:** Converting "work runs late" into "I feel like I've already lost the evening" is the difference between a plan that fires and one that doesn't. It's worth a screen for users who chose the 3-minute path. It's not worth adding to a 45-second one.

---

## C. Product-level

### D10 — Habits graduate. Not negotiable.

**Closes:** PRD §12.4
**Decision:** Ship graduation. Habits leave tracking at sustained SRBAI, reminders stop, and we say so in marketing.

**Why:** The alternative is a product with a structural interest in the user never succeeding. Whatever it costs in subscription months, it's the thing that makes every other claim in the PRD credible — and a user who graduated a habit and knows we let it go is the only kind of user who recommends this without qualification.

---

### D11 — Cue-stability feedback appears at creation, never after a failure.

**Closes:** PRD §12.3
**Decision:** Anchor stability is surfaced when a habit is created or re-planned (Onboarding §4.1). It is prohibited in the recovery break.

**Why:** "This cue is unstable" is useful before you commit and is a verdict on your life afterwards. Same information, opposite effect, entirely a function of timing. Told early it's help with a design problem; told after three misses it reads as *your week is too chaotic for this to work*.

**Changes:** Failure Layer §11.3.4 drops the cue-stability arm from the recovery-break MRT.

---

### D12 — No depression or anxiety screening in Phase 1. At all. *(Changes scope)*

**Closes:** the PHQ-8 question left standing in PRD §4.6.1 and §11
**Decision:** Ship WHO-5 only. PHQ-8 and GAD-7 do not appear in Phase 1, not even opt-in, not even in a settings menu.

**Why:** We were going to collect distress data we have no ability to respond to. PHQ-8 sidesteps the item-9 crisis obligation, but a user scoring 19 on PHQ-8 is a user in trouble, and our plan was to note it and show them a journey. Screening you can't act on serves the research platform, not the person answering.

WHO-5 is a wellbeing measure, reads as one, and carries no implied duty we can't meet.

**Unblocks:** the crisis protocol stops being a Phase 1 dependency and becomes a Phase 2 prerequisite for the Guided tier only — where a human is present and escalation is real.

**Cost:** weaker Phase 1 outcome claims. We can say wellbeing improved; we can't say depressive symptoms did. That's the correct thing to be able to say at this stage anyway.

---

## D. Guided tier

### D13 — Coach caseload is capped by memory. *(Costs money)*

**Closes:** PRD §12.1
**Decision:** 150 users per coach at launch. The number comes from the requirement that a coach can read a user's history before replying and recall them without prompting. Price the tier to fit the caseload; do not fit the caseload to the price.

**Why:** The entire evidence base for supportive accountability rests on a person who notices. A coach at 400 users is a queue, and a user can tell within two exchanges. At that point we're charging $29 for templated replies and the differentiator is gone.

**Consequence:** the Guided tier may need to price above $39, or launch capped and waitlisted. Both are better than launching it hollow. Revisit only with evidence about quality at higher ratios, never with a margin target.

---

### D14 — The Guided tier does not launch before the crisis protocol.

**Decision:** Formalizes what Failure Layer §8 implied. Coaches will receive disclosures they aren't qualified for; that's certain, not a risk.

**Why:** Putting a person in the path creates a duty. A user who tells a coach something serious and gets a scripted deflection has been failed worse than one who never had a coach.

---

## E. Stack

### D15 — Accept the five chokepoints, on the record.

**Closes:** Stack §12.1. Xcode, app stores, APNs, FCM-as-transport, StoreKit. External claim is "self-hosted open source infrastructure, no third-party SDKs in the client" — true, and stronger than a claim we'd have to qualify.

### D16 — Nothing the user depends on travels by email. *(Resolves the exception)*

**Closes:** Stack §12.2
**Decision:** Don't take the deliverability exception. Instead, remove email from the critical path: reminders, recovery, and coach messages are push and in-app only. Email carries account verification, receipts, and data-export links — low volume, self-hosted Postal, and nothing that breaks the product if it lands in spam.

**Why:** The exception existed because deliverability failure could silently break the failure layer. Making email non-load-bearing solves that better than outsourcing it — a user whose recovery message went to spam has been failed regardless of who sent it.

**Bonus:** honors the open-source constraint without a carve-out.

### D17 — AGPL permitted for internal infrastructure.

**Closes:** Stack §12.3. One legal opinion covering the class, CI check flagging local patches to AGPL dependencies. Prohibited in anything the client talks to directly.

### D18 — Python/FastAPI.

**Closes:** Stack §12.4. The ML and research obligations are long-lived and Python-native; the scheduling problem is solvable anywhere.

### D19 — Penpot yes, F-Droid yes (Phase 2).

**Closes:** Stack §12.5–12.6. Penpot is sufficient for this product's design needs, and the constraint is worth more than the ecosystem gap. F-Droid is a cheap build variant that serves the privacy-forward segment we're explicitly courting — and it's the one place UnifiedPush works, so it's also our only fully-open push path.

---

## F. What changed, consolidated

| Doc | Section | Change | Decision |
|---|---|---|---|
| Failure Layer | §2.1, §3.1 | No push-side recovery at `lapsed_1`; pull/push distinction added | D1 |
| Failure Layer | §4.4 | Shrink is time-boxed to 7 days with restore prompt | D2 |
| Failure Layer | §4.6 | Quit Track scope narrowed; clinical categories excluded from picker | D4 |
| Failure Layer | §4.2 | WOOP-offer branch added for `if_then` plans | D5 |
| Failure Layer | §11.2–11.3 | MRT arms move to `lapsed_2`; cue-stability arm dropped | D1, D11 |
| Onboarding | §2, §3.1 | Flow forks into quick setup / proper setup; timers 20s → 15s | D5 |
| Onboarding | §3.2 | Obstacle word limit removed | D6 |
| Onboarding | §5.4, §10 | PHQ-8/GAD-7 removed from Phase 1 entirely | D12 |
| Onboarding | §7 | Paywall fixed at day 7 | D7 |
| PRD | §4.6.1 | Phase 1 battery is WHO-5, MCTQ, SRBAI, BREQ-3, PSS-10 — no PHQ/GAD | D12 |
| PRD | §4.9 | Free tier includes the full failure layer, permanently | D8 |
| PRD | §4.5.4 | 150:1 caseload cap; tier priced to fit | D13 |
| PRD | §10 | Crisis protocol moves from Phase 1 blocker to Phase 2 Guided prerequisite | D12, D14 |
| Stack | §4 | Email removed from the critical path | D16 |

---

## G. The three that cost us

Stated plainly so nobody has to rediscover them in a pricing review:

1. **D7 — day-7 paywall.** Slower conversion than behavioral gating. Taken because gating on completions charges the people it's working for and lets the people it isn't drift away.
2. **D8 — free failure layer.** Our most expensive feature, given away, including to users who cancel. Taken because meeting our differentiator as a locked door is worse than not having it, and because withdrawing lapse support from someone who just cancelled would be the most cynical thing in the product.
3. **D13 — 150:1 caseload.** Caps Guided-tier margin and may force a higher price or a waitlist. Taken because supportive accountability works through a person who notices, and a user knows within two exchanges whether they're talking to one.

If a later review reverses any of these, it should reverse them explicitly and say so, rather than letting them erode through defaults.

---

## H. Still genuinely open

Two, and neither blocks Phase 1:

1. **Does the recovery protocol move lapse recovery rate?** (PRD §12.2) An empirical question, not a decision. The holdout is configured; it answers itself by month three. If it doesn't move, the spine of the product needs rebuilding and we'll know early — which is the point of putting it first.
2. **Quit Track clinical categories.** Blocked on review per D4, not undecided. Revisit with a clinician in Phase 2.
