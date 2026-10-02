# Build Spec — Crisis Protocol

**Implements:** PRD §11 (clinical safety), D12 (precondition for clinical instruments), D14 (precondition for the Guided tier)
**Phase:** 2 — blocking for the Guided tier and for any return of PHQ-8/GAD-7
**Version:** 1.0 — **DRAFT, requires clinical and legal sign-off before any part ships**
**Date:** 8 August 2026

> **Read this first.** This document is drafted by a product author, not a clinician. Every threshold, script, and routing rule below is a starting position for review by a qualified clinician and by counsel. Nothing here ships on product judgment alone. §12 lists what sign-off requires.

---

## 1. What this protocol is, and is not

**It is:** a defined way to recognise that a person may be in danger, respond without making things worse, route them to help that actually exists, and record what happened.

**It is not:** a crisis service, a monitoring system, a substitute for care, or a detection product.

That distinction governs every design choice below. The most common way products in this category cause harm is by implying a level of vigilance they do not have — a user who believes someone is watching may rely on it, and that reliance is itself a risk.

### 1.1 The inversion

The instinct is to build detection: scan text, flag risk, intervene. **We do the opposite, and put nearly all the weight on user-initiated access.**

| Approach | Weight | Why |
|---|---|---|
| **Always-available help, findable in ≤2 taps from anywhere** | Primary | Works without detection, without false positives, without anyone being profiled. Available at 3am when nobody is reading anything |
| **Human-noticed disclosure** (coach reads a message) | Secondary | Reliable within its hours. Bounded, accountable, trainable |
| **Automated text scanning** | **Not built in Phase 2** | See §4 |

---

## 2. Standing commitments

These are product commitments, stated in-app and in the terms, not just internal policy.

1. **We are not monitoring you.** Stated plainly wherever a user writes free text. No "we're keeping an eye out" language anywhere, ever.
2. **We never contact emergency services on a user's behalf without their explicit, contemporaneous consent.** See §7.
3. **We never withhold access to the product as a response to disclosure.** Locking someone out of their coping plans because they said something alarming is a punishment dressed as safety.
4. **Coach response hours are published and honest.** Users are told the actual window and the actual expected response time, including that it is not overnight.
5. **Crisis resources are available without an account, without a subscription, and offline.**

---

## 3. Always-available help

The centrepiece. Built first, and it is the one part of this document that could ship in Phase 1 if we chose to.

### 3.1 Placement

- Persistent entry in the main menu, labelled plainly: **"Urgent help"**. Not buried under Settings → Support → Resources.
- Present on every free-text surface (journal, reflection, obstacle field, coach composer) as a quiet, always-visible link.
- Reachable in **≤2 taps from any screen**.
- Works logged-out, unsubscribed, and offline.

### 3.2 What it contains

1. **Local crisis line**, resolved by device region (§3.3)
2. **Text/chat option** where one exists in that region — many people cannot make a voice call in crisis, and this is not a minor detail
3. **Local emergency number** as the universal fallback
4. **"I'm not in danger but I'm struggling"** branch → non-emergency options: warmlines, finding a therapist, the app's own regulation protocols
5. **No login wall, no interstitial, no analytics event that could be mistaken for a health record**

Point 4 matters. Most people opening this screen are not in immediate danger, and a screen that offers only emergency options tells them they are in the wrong place.

### 3.3 Resource data — the maintenance problem

A stale crisis number is worse than no number, and this data goes stale constantly.

**Approach:**
- Source from a maintained directory (e.g. Find A Helpline / IASP) rather than a hand-built table
- **Refresh weekly**; cache locally so it works offline
- Cache carries a `verified_at` date; if older than 90 days, the screen additionally shows the local emergency number prominently
- **Manual verification of the top 10 markets each quarter**, owned by a named person, with the check recorded

**Never hardcode a single number.** Regional coverage differs enormously, several countries have no dedicated line, and numbers change.

---

## 4. Why we are not building automated detection in Phase 2

This is the section most likely to be argued with, so the reasoning is explicit.

**False positives are harmful, not neutral.** Flagging someone who wrote "this is killing me" about their commute and responding with crisis resources is intrusive, embarrassing, and teaches them not to write honestly in the product — which removes the one signal a human might genuinely have noticed.

**False negatives are the norm and create false assurance.** Keyword and classifier approaches on short informal text perform poorly on the cases that matter most, which are frequently oblique. Once a detection system exists, its existence gets relied on internally — "the system would have caught it" — and that reliance is unwarranted.

**It creates a health record we cannot hold.** A risk score attached to a user is exactly the "consumer health data" that WA MHMD and the FTC HBNR regulate most tightly (STACK §2), and it is the highest-sensitivity data we could possibly generate.

**It changes what we are.** A product that scores users for suicide risk has taken on a duty it cannot discharge, in a jurisdiction-specific way we have not analysed.

**What we build instead:** §3 (always available, no detection needed) and §5 (a trained human who can read).

**Revisit when:** there is a clinician on staff, a defined duty analysis from counsel, 24/7 coverage, and evidence that a specific detection approach outperforms the alternative in *our* population. Not before.

---

## 5. Coach protocol

Applies once the Guided tier exists. A coach is the only routine path by which we learn a user may be in danger.

### 5.1 Coaches are not clinicians

Trained non-clinicians. Scope boundary from PRD §4.5.4 is absolute: **do not diagnose, do not treat, do not counsel on risk.** The coach's entire job in this situation is: acknowledge, do not escalate the emotional temperature, offer the resource, stay present within their hours, and hand off.

### 5.2 Recognition — what a coach is trained to notice

Not a keyword list. Trained categories, with examples, in the onboarding curriculum:

- Explicit statements of intent to end one's life or to self-harm
- Statements of hopelessness paired with finality ("won't be a problem much longer," giving things away)
- Disclosure of abuse, or of being unsafe where they live
- Disclosure of acute psychiatric symptoms (not sleeping for days, hearing voices)
- Disclosure of harm to another person
- A marked, abrupt change in tone or coherence from a user the coach knows

The last one is why the 150:1 caseload cap (D13) is a safety control, not only a quality one. **A coach who does not remember you cannot notice that you have changed.**

### 5.3 The response script

Trained, practised, and available in the coach console. Not improvised.

**Step 1 — Acknowledge, directly, without alarm.**
> "Thank you for telling me that. I'm glad you did."

Never: minimising ("everyone feels that sometimes"), alarm ("I'm really worried!!"), or advice.

**Step 2 — Ask the direct question, if intent is ambiguous.**
> "I want to make sure I understand — are you thinking about ending your life?"

Asking directly does not increase risk; the evidence is consistent on this, and the fear of asking is the more common failure. Coaches are trained and rehearsed on this specific sentence, because it is the one people avoid.

**Step 3 — Name the boundary honestly.**
> "I'm not a therapist and I'm not able to help with this the way you need. I don't want to pretend otherwise."

**Step 4 — Offer the resource, concretely.**
> "[Local line], and they have a text option. Would you be willing to contact them now?"

**Step 5 — Stay, within honest limits.**
> "I'm here for the next while. I'm not here overnight — I want you to know that rather than find out."

**Step 6 — Hand off** to the on-call reviewer (§6) within 15 minutes.

### 5.4 What a coach never does

- Never promises confidentiality they cannot keep, and never promises to tell no one
- Never contacts emergency services unilaterally (§7)
- Never contacts a user's family, employer, or emergency contact
- Never continues a risk conversation past the handoff
- Never closes the thread, marks it resolved, or lets it lapse silently

### 5.5 Training and support

- Recognised crisis-response training before taking any caseload (ASIST, safeTALK, or equivalent — clinician to specify), refreshed annually
- Rehearsed roleplay of §5.3 during onboarding, not a read-through
- **Debrief with the clinical supervisor after every crisis contact, without exception.** Coaches carrying these conversations alone is how coaches leave, and how the next conversation goes worse
- Access to the supervisor during shift, not by ticket
- Explicit permission — stated in writing — to step back from a user without justifying it

---

## 6. Escalation and coverage

### 6.1 Roles

| Role | Responsibility | Availability |
|---|---|---|
| Coach | Recognise, respond per §5.3, hand off | Published hours |
| **On-call reviewer** | Receives handoff, reviews, decides follow-up, records | Same hours + 2h tail |
| **Clinical supervisor** | Owns the protocol, debriefs coaches, reviews every case weekly | Business hours, on-call for consult |

### 6.2 We are not 24/7, and we say so

A startup with one coach per 150 users cannot staff overnight cover, and pretending otherwise is the dangerous option.

**Therefore:**
- Coach hours are stated at Guided-tier signup, in the coach composer, and in the auto-reply outside hours
- The out-of-hours auto-reply is honest and useful, not reassuring:

> No one is reading messages right now — the team is back at [time]. If you need someone tonight, [local line] is 24 hours and they have a text option.

- **The always-available help (§3) is the 24/7 answer, and it is a real one.** A crisis line staffed round the clock by trained people is better than an app, and saying so is not an abdication.

### 6.3 Follow-up

The on-call reviewer decides one of:
- **Coach follow-up** at next shift, with a specific check-in
- **Supervisor contact**, where the disclosure exceeds coach scope
- **No further action**, recorded with reasoning

Every case is reviewed by the clinical supervisor within 7 days regardless of the decision.

---

## 7. Emergency services — the hard line

**We do not contact emergency services on a user's behalf without their explicit, contemporaneous consent.**

Two reasons, and the first is the one that matters.

**Non-consensual welfare checks cause documented harm.** Police response to mental-health crisis has produced deaths, arrests, involuntary hospitalisation, and lasting deterrence from seeking help. A person who learns that disclosing distress to an app summons police will not disclose again — to us or to anyone. The intervention that feels most protective is frequently the one that does the most damage.

**We also cannot do it competently.** We do not reliably know where a user is. Coarse region is not an address. Acting on a guess is worse than not acting.

**What we do instead, when a coach believes someone is in immediate danger:**
1. Stay in the conversation
2. Ask directly whether they will contact the crisis line, or let the coach stay while they do
3. Ask whether there is someone with them, or someone they would let the coach help them contact
4. Offer to remain present until they have made contact
5. Hand off to the reviewer immediately, in parallel

**The single documented exception** requires counsel to define: a user who provides their own location and explicitly asks us to call for help. Even then, the reviewer decides, not the coach, and it is recorded.

This position must be reviewed against duty-to-warn and mandatory-reporting obligations in every jurisdiction we operate in — **including the possibility that some jurisdiction requires something different, in which case the policy changes there and we say so.**

---

## 8. Data handling

Crisis disclosures are the most sensitive data this company will ever hold.

| Rule | Detail |
|---|---|
| **Minimal record** | What was disclosed (brief factual note), what the coach did, what was decided. **Not** the raw message text beyond what is necessary |
| **Access** | Coach involved, on-call reviewer, clinical supervisor. Nobody else. Not engineering, not analytics, not support |
| **Never in the warehouse** | Crisis records do not flow to the analytics pipeline, dbt, or any dashboard. Physically separate store |
| **Never a user attribute** | No `risk_flag` on the user record. No segmentation, no cohort, no targeting, no exclusion from campaigns based on it |
| **Retention** | Defined by counsel. Default to the shortest defensible period |
| **Export/deletion** | Interacts with the user's PRD §6.2 rights in ways counsel must resolve — a deletion request against a safety record is a genuine conflict, not an oversight |
| **Breach class** | Treated as the highest-severity category under the FTC HBNR and WA MHMD |

---

## 9. Non-Guided users

Most users will never have a coach. They get:

- §3 always-available help, on every free-text surface
- No monitoring, and a plain statement of that fact
- Support-email disclosures routed to the on-call reviewer under the same protocol (support staff receive §5.3 training as well — a distressed email is the most likely non-coach path)

**No detection, no flagging, no automated outreach.** A user who writes something alarming in a private journal receives exactly what they expect: privacy.

---

## 10. Interaction with D12 — when clinical instruments can return

PHQ-8 and GAD-7 were removed from Phase 1 because we could not act on what they told us. They may return only when **all** of the following hold:

- [ ] This protocol is signed off by a clinician and by counsel
- [ ] A clinical supervisor is on staff or under standing contract
- [ ] Coach coverage exists with published hours and a live escalation path
- [ ] A defined response exists for **each severity band**, written before the instrument ships
- [ ] Users are told what happens with their scores, before they answer
- [ ] Item 9 of PHQ-9 remains excluded unless the response to a positive endorsement is defined, staffed, and rehearsed

Screening without a response is data collection with a clinical veneer. The bar is the response, not the instrument.

---

## 11. Acceptance criteria

Blocking for the Guided tier:

- [ ] Urgent help reachable in ≤2 taps from every screen, logged-out, unsubscribed, and offline
- [ ] Resource data refreshes weekly, carries `verified_at`, falls back to the local emergency number past 90 days
- [ ] Top-10-market resources manually verified, with a named owner and a recorded date
- [ ] "I'm not in danger but I'm struggling" branch exists and is not an afterthought
- [ ] No monitoring language anywhere; explicit non-monitoring statement on every free-text surface
- [ ] Coach console surfaces the §5.3 script inline, not in a wiki
- [ ] Handoff to on-call reviewer within 15 minutes, enforced and alerted
- [ ] Out-of-hours auto-reply states real hours and offers the 24h line
- [ ] Every coach holds current crisis-response certification; verified at onboarding and annually
- [ ] Debrief recorded after every crisis contact
- [ ] Crisis records stored separately; verified absent from the analytics pipeline
- [ ] No `risk_flag` or equivalent exists on the user record
- [ ] Clinician sign-off recorded
- [ ] Counsel sign-off recorded, covering duty-to-warn, mandatory reporting, and the §7 position per jurisdiction

---

## 12. Sign-off requirements

| Reviewer | Must confirm |
|---|---|
| **Clinician** (crisis-response background) | §5.2 recognition categories · §5.3 script wording · §5.5 training standard · §10 readiness bar |
| **Counsel** | §7 emergency-services position per jurisdiction · duty-to-warn and mandatory-reporting exposure · §8 retention and the deletion conflict · whether this protocol changes our regulatory classification |
| **Clinical supervisor** (once hired) | Operational feasibility of §6 coverage at actual staffing |

**None of this ships on product judgment.** The document exists so that the review has something concrete to correct, which is faster and safer than asking a clinician to invent it from scratch.

---

## 13. Open questions

1. **What are honest coach hours at launch?** One coach, 150 users, is roughly a half-time role. Coverage might be 5 days × 6 hours. That is a defensible answer only if stated plainly, and it should be decided before the tier is priced.
2. **Does the §7 position survive counsel review in every market?** Some jurisdictions may impose obligations that conflict with it. The policy is then jurisdiction-specific, and users in those markets are told.
3. **Is the deletion conflict in §8 resolvable?** A user's right to erase versus a safety record we may be obliged to keep. Needs a real answer, not a footnote.
4. **Should §3 ship in Phase 1?** It requires no coaches, no clinician, and no detection — only accurate data and honest copy. **The argument for shipping it in Phase 1 is that it costs a sprint and it is the single most useful thing in this document.** The argument against is that it implies a duty of care we have not yet analysed. This is the first question for counsel, and I would put it to them in week 0.
