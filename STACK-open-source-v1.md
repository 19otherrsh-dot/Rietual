# Technical Stack — Open Source Only

**Constrains:** PRD §6 (Technical Requirements), §8.1 (AI), §8.8 (Labs)
**Version:** 1.1
**Date:** 8 August 2026
**Amended by:** DECISIONS-v1 — D15, D16, D17, D18, D19 applied below

**Constraint as interpreted:** every tool, library, and service we *choose* must be OSI-approved open source and self-hostable. This is a constraint on our stack, not on the platforms we ship to.

---

## 1. The three categories

Any honest version of this constraint has to separate them, because one of the three cannot be satisfied.

| Category | Definition | Status |
|---|---|---|
| **A. Tools we choose** | Backend, database, analytics, CI, experimentation, ML | **Fully satisfiable.** All of §3–§8 below |
| **B. Platform APIs** | HealthKit, Health Connect, Screen Time, StoreKit, APNs | **Not satisfiable, and not a tool choice.** These are the OS surfaces the product decided to integrate with in PRD §6.3. Using HealthKit is not "using a proprietary tool" any more than compiling for ARM is |
| **C. Mandatory proprietary chokepoints** | Xcode, App Store / Play Store, code signing, push transport, IAP billing | **Not satisfiable. Requires an explicit decision** — see §2 |

§2 is the part to read before the stack tables. Everything else is straightforward.

---

## 2. Hard boundaries — decisions required

These are unavoidable given PRD §6.1's decision to ship native iOS and Android. Each needs an explicit accept/reject, because "we use only open source" is not a statement we can make truthfully without them being on the record.

| Chokepoint | Why unavoidable | Options |
|---|---|---|
| **Xcode + Apple toolchain** | The only supported way to build and sign iOS binaries. Swift itself is Apache 2.0; the IDE and signing chain are not | Accept. No alternative exists |
| **App Store / Play Store** | Distribution. F-Droid is possible for Android as a *secondary* channel; iOS sideloading is EU-only and impractical for our audience | Accept, with optional F-Droid build for the privacy-forward segment |
| **APNs** | There is no way to deliver a push notification to a stock iOS device except through Apple's gateway | Accept. Mitigate by talking to APNs directly from our own server with an open source client library — no Firebase, no OneSignal, no vendor in the path |
| **Android push** | FCM is proprietary and is the only reliable transport on stock Android | Accept FCM **as transport only** — payloads encrypted, no Firebase SDK, no Firebase Analytics, HTTP v1 API called from our server. UnifiedPush works only for de-Googled devices; ship it in the F-Droid build |
| **StoreKit / Play Billing** | Platform rules require them for digital subscriptions | Accept. But **no RevenueCat or similar** — receipt validation is our own service (§4.6), which is just code we write and can open source |
| **Wearable APIs** (Garmin, Fitbit, Oura, Whoop) | Proprietary web APIs | These are data sources, not tools. Accept, or drop the integration. No SDK gets embedded — server-to-server OAuth only |

**Recommended framing for external use:** "self-hosted, open source infrastructure; no third-party SDKs in the client." That is both true and a stronger privacy claim than "100% open source," which we cannot make.

**Strategic note.** This constraint is *aligned* with PRD §6.2, not in tension with it. The single most common route to an FTC HBNR violation in this category is an analytics or ad SDK quietly exfiltrating health-adjacent events — and the launch-blocking SDK egress audit becomes near-trivial when the answer is "there are no third-party SDKs." The constraint materially lowers our largest regulatory exposure.

---

## 3. Client

| Layer | Choice | License | Notes |
|---|---|---|---|
| iOS language | Swift | Apache 2.0 | |
| iOS UI | SwiftUI | Proprietary framework, no alternative | Category B |
| Android language | Kotlin | Apache 2.0 | |
| Android UI | Jetpack Compose | Apache 2.0 | |
| Local DB (iOS) | SQLite + **GRDB.swift** | Public domain / MIT | |
| Local DB (Android) | SQLite + **Room** | Apache 2.0 | |
| Offline sync | Event-sourced sync over our own API | — | See §3.1 |
| Charts | **Swift Charts** / **Vico** (Android) | Proprietary / Apache 2.0 | iOS: consider **DGCharts** (Apache 2.0) for full open source parity |
| Audio playback | AVFoundation / **Media3 ExoPlayer** | Proprietary / Apache 2.0 | |
| On-device speech | **whisper.cpp** | MIT | §7.2 — also satisfies PRD §6.2's on-device preference |
| Crash reporting | **GlitchTip** SDK (Sentry-compatible clients) | See §9 trap #1 | Self-hosted |
| Analytics | **PostHog** self-hosted, or first-party events to our own API | See §9 trap #2 | Prefer first-party — no SDK at all |
| Build/signing automation | **fastlane** | MIT | |

### 3.1 Offline sync

PRD §6.1 requires offline core functionality and real-time cross-device sync. Evaluated:

| Option | License | Assessment |
|---|---|---|
| **Event-sourced sync, in-house** | ours | **Recommended.** Habit logging is append-mostly with rare conflicts; a per-device event log with last-write-wins on habit config and union on completions covers ~all real cases. Cheapest thing that works |
| CR-SQLite | Apache 2.0 / MIT | Good CRDT-over-SQLite option if conflict handling gets hairier than expected |
| ElectricSQL | Apache 2.0 | Postgres↔SQLite sync; more machinery than we need at Phase 1 |
| Automerge | MIT | Right answer if journals become collaborative (§8.9 family features). Overkill now |

Recommendation: in-house event sourcing for Phase 1, with CR-SQLite as the identified escape hatch. Do not adopt a sync framework before we have a conflict we can't handle.

---

## 4. Backend

| Layer | Choice | License | Notes |
|---|---|---|---|
| Language/framework | **Python + FastAPI**, or **Elixir + Phoenix** | MIT / Apache 2.0 | See §4.1 |
| Primary DB | **PostgreSQL** | PostgreSQL License | Native partitioning for time-series; skip TimescaleDB (§9 trap #3) |
| Cache / queue broker | **Valkey** | BSD-3 | Not Redis — see §9 trap #4 |
| Job queue | **Celery** (Python) / **Oban** (Elixir) | BSD-3 / Apache 2.0 | Scheduled occurrences, miss detection, reminder fading |
| Auth | **Ory Kratos** or **Keycloak** | Apache 2.0 | Kratos if we want headless; Keycloak if we want enterprise SSO (§8.5) for free |
| Object storage | **SeaweedFS** or **Garage** | Apache 2.0 / AGPLv3 | Audio library. Not MinIO — §9 trap #5 |
| CDN/edge | **Nginx** + **Varnish** on our own edge nodes | BSD-2 / BSD-2 | A commercial CDN is a service, not a tool; if used, it carries no user data beyond audio requests |
| Media encoding | **FFmpeg** | LGPL/GPL | Audio transcode for the coaching library |
| Search | **Meilisearch** | MIT | Content library search |
| Email (account only) | **Postal** | MIT | Self-hosted MTA. **Low volume, nothing behavior-critical** — see §4.2 |
| Email (campaign) | **Listmonk** | AGPLv3 | Fresh-start re-engagement (§4.1.5). Best-effort; never the only channel |
| APNs client | **apns2** (Go) or **PyAPNs2** | MIT | Direct to Apple, no vendor |
| IAP validation | in-house service | ours | §2, StoreKit 2 + Play Developer API |

### 4.1 Language choice

**Phoenix/Elixir is the better technical fit** — the product is overwhelmingly scheduled-timer-plus-notification work (miss detection at window close + 2h, reminder fading, spaced retrieval probes, coach queue SLAs), which is exactly what the BEAM is good at, and Phoenix Channels handle sync push cleanly.

**FastAPI/Python is the better fit for §7** — the ML, MRT analysis, and research tooling are all Python-native, and hiring is easier.

**Decision: Python/FastAPI (D18)**, with the scheduling layer as its own service. The ML and research obligations in PRD §8.1/§8.8 are load-bearing and long-lived; the scheduling problem is solvable in any language with Celery beat and a decent clock. Don't split the stack for a problem that isn't hard yet.

### 4.2 Nothing the user depends on travels by email (D16)

v1.0 of this document flagged self-hosted transactional email as the strongest candidate for an exception to the open-source constraint, because deliverability failure could silently break the failure layer's delivery path.

**Better answer: take email off the critical path entirely.**

| Channel | Carries |
|---|---|
| **Push + in-app** | Reminders, recovery breaks, coach messages, everything behavioral |
| **Email** | Account verification, receipts, data-export links, best-effort re-engagement |

A user whose recovery message went to spam has been failed regardless of who sent it — so the fix was never a better vendor, it was not putting it in email. What remains is low-volume and non-urgent, which is exactly the profile a self-hosted Postal handles without heroics.

**Result: the constraint holds with no carve-out**, and the product is more robust than the version that outsourced deliverability.

---

## 5. Data & analytics

| Need | Choice | License |
|---|---|---|
| Product analytics | **PostHog** self-hosted | §9 trap #2 |
| Warehouse | **PostgreSQL** → **ClickHouse** when volume demands | Apache 2.0 |
| Transformation | **dbt-core** | Apache 2.0 |
| Orchestration | **Dagster** or **Apache Airflow** | Apache 2.0 |
| BI / dashboards | **Metabase** (OSS edition) or **Apache Superset** | AGPLv3 / Apache 2.0 |
| Notebooks | **Jupyter** | BSD-3 |

**First-party event collection is preferred over any analytics SDK.** Events go to our own endpoint, on our own schema, and we control retention and deletion — which is what makes PRD §6.2's one-tap export and delete actually implementable rather than aspirational.

---

## 6. Experimentation & research (PRD §8.8)

This is where the constraint pays off most, because reproducibility is an IRB requirement and open tooling is what makes it credible.

| Need | Choice | License | Notes |
|---|---|---|---|
| Feature flags | **Unleash** | Apache 2.0 | Core is genuinely Apache 2.0 |
| Experiment assignment & analysis | **GrowthBook** | MIT | Handles A/B; **not** MRT-aware |
| **MRT randomization** | in-house | ours | See §6.1 |
| MRT analysis | **R** + `geepack`, or Python `statsmodels` | GPL-2 / BSD-3 | Weighted centered least squares estimator |
| Contextual bandits | **River** (online learning) | BSD-3 | §8.1 JITAI |
| Reproducibility | **Docker**/**Podman** + pinned lockfiles | Apache 2.0 | IRB submissions reference exact images |

### 6.1 Why MRT randomization must be in-house

No open source (or commercial) experimentation platform implements micro-randomized trials. GrowthBook, Unleash, and Flagsmith all assume **user-level** assignment that persists. An MRT randomizes **at every decision point** — each miss detection, per PRD §11.2 — with a receptivity gate that can veto the decision point entirely.

This is ~200 lines of code, not a platform:

```
on decision_point(user, habit, miss):
    if not receptive(user, habit, now):     # paused, bad week, cap reached
        log(decision_point, randomized=False, reason=...)
        return
    arm = weighted_choice(["full", "minimal", "none"], p=[.4,.4,.2])
    log(decision_point, arm, tailoring_vars, timestamp)
    deliver(arm)
```

The logging schema matters more than the randomizer. Every decision point must be recorded **including the ones where we chose not to intervene** — non-receptive decision points are what make the causal estimand well-defined, and omitting them is the most common way an MRT gets ruined before analysis.

---

## 7. ML & AI (PRD §8.1)

### 7.1 The open-weights honesty problem

**"Open weights" is frequently not open source, and the distinction matters for a company positioning on scientific and licensing transparency.**

| Model family | Actual license | OSI open source? |
|---|---|---|
| **OLMo 2** (AI2) | Apache 2.0, open training data | **Yes — genuinely open** |
| **Qwen 2.5 / 3** (most sizes) | Apache 2.0 | Yes (verify per-size; some variants differ) |
| **Mistral** (open models) | Apache 2.0 | Yes (the open ones; their commercial models are not) |
| **Llama 3.x / 4** | Meta Community License | **No.** MAU threshold, naming requirements, acceptable-use policy |
| **Gemma** | Gemma Terms of Use | **No.** Use restrictions |
| GPT-4o, Claude, Gemini | Proprietary API | No |

**Recommendation:** Qwen or Mistral Apache-2.0 checkpoints for production; OLMo where full data provenance matters (research publications under §8.8, where reviewers may ask what the model was trained on). **Llama and Gemma are excluded** despite being the popular defaults — accepting a source-available license while claiming an open source stack is precisely the kind of quiet inconsistency §5.2 of the PRD exists to prevent us from tolerating.

### 7.2 Stack

| Need | Choice | License |
|---|---|---|
| Training/inference | **PyTorch** | BSD-3 |
| Serving | **vLLM** | Apache 2.0 |
| Local/edge inference | **llama.cpp** | MIT |
| Speech-to-text | **whisper.cpp** (on-device) | MIT |
| Text-to-speech | **Piper** or **Coqui TTS** | MIT / MPL 2.0 |
| Classical ML | **scikit-learn** | BSD-3 |
| Online learning / bandits | **River** | BSD-3 |
| Experiment tracking | **MLflow** or **Aim** | Apache 2.0 |

### 7.3 Quality tradeoff — stated plainly

PRD §8.1's voice-first onboarding assumed a frontier proprietary model. A self-hosted Qwen or Mistral at a size we can afford to serve **will be noticeably worse** at open-ended conversational intake — more brittle, more prone to losing the thread of a structured assessment.

Three ways this resolves, in order of preference:

1. **Narrow the task.** Voice intake doesn't need open-ended conversation; it needs slot-filling against a fixed assessment schema. A 7–14B model with constrained decoding does this well. **This is the right answer, and it's a better product anyway** — a structured intake that reliably captures MCTQ and BREQ-3 responses beats a charming one that doesn't.
2. **On-device ASR + templated dialogue.** whisper.cpp transcribes, the dialogue logic is deterministic. Strongest privacy story (PRD §6.2), zero inference cost, no LLM failure modes in a first-run experience.
3. **Defer voice onboarding** past Phase 2 rather than compromise the constraint.

The one place a self-hosted model is clearly *sufficient* today: generating coping-plan response suggestions (§5.3 of the failure-layer spec) from a class-indexed library, where the model is ranking and lightly rewording from a curated set rather than generating freely. Do that first.

**Never route the recovery break (failure-layer §4) through a generative model.** That copy is tone-critical, reviewed by an advisor and a segment participant, and passes seven normative rules. It is a template with variable slots. An LLM cannot be held to §6 rule 2.

---

## 8. Infrastructure & ops

| Layer | Choice | License |
|---|---|---|
| Containers | **Podman** / **Docker Engine** | Apache 2.0 |
| Orchestration | **Kubernetes** (or **Nomad** if the team is small) | Apache 2.0 / MPL 2.0 |
| IaC | **OpenTofu** | MPL 2.0 — not Terraform, §9 trap #6 |
| Config mgmt | **Ansible** | GPL-3 |
| Metrics | **Prometheus** + **Grafana** | Apache 2.0 / AGPLv3 |
| Logs | **Grafana Loki** | AGPLv3 |
| Tracing | **OpenTelemetry** + **Jaeger** | Apache 2.0 |
| Errors | **GlitchTip** | §9 trap #1 |
| CI/CD | **Forgejo Actions** or **Woodpecker CI** | MIT / Apache 2.0 |
| Source hosting | **Forgejo** self-hosted | MIT |
| Secrets | **OpenBao** | MPL 2.0 — the open fork of Vault, §9 trap #6 |
| Design | **Penpot** | MPL 2.0 — real tradeoff, §11 |
| Localization | **Weblate** | GPL-3 |
| Docs | **Docusaurus** / **MkDocs** | MIT / BSD-2 |

---

## 9. License traps

The failure mode of an open-source-only mandate is adopting a tool that *was* open source. Each of these has bitten teams recently.

| # | Tool | Trap |
|---|---|---|
| 1 | **Sentry** | Relicensed to **BSL 1.1** in 2019 — source-available, not OSI. Self-hosting is permitted for non-competing use, but it does not satisfy the constraint. **Use GlitchTip** (Sentry-SDK-compatible). Verify GlitchTip's current license at adoption |
| 2 | **PostHog** | Main repo is MIT, but `ee/` directories are proprietary. Self-hosting the OSS build is compliant; do not enable enterprise features. **Alternative: skip it and collect first-party events to our own API** — fewer moving parts and a better privacy story |
| 3 | **TimescaleDB** | Community features are under the **Timescale License (TSL)**, not Apache 2.0. Plain PostgreSQL declarative partitioning covers our time-series needs |
| 4 | **Redis** | Moved to RSALv2/SSPL in 2024; AGPLv3 was added back in 2025. History is volatile. **Use Valkey** (BSD-3, Linux Foundation) and stop tracking the drama |
| 5 | **MinIO** | AGPLv3, and the community edition had significant features removed in 2025. **Use SeaweedFS** (Apache 2.0) or **Garage** (AGPLv3, if AGPL is acceptable per §9.1) |
| 6 | **Terraform / Vault** | Both moved to BSL. **Use OpenTofu and OpenBao** — the Linux Foundation forks |
| 7 | **Elasticsearch** | SSPL/Elastic License era; AGPL option added 2024. **Use OpenSearch** (Apache 2.0) if we need it at all |
| 8 | **Docker Desktop** | Proprietary and commercially licensed. The **Docker Engine** is Apache 2.0. Use Podman or Colima on developer machines |
| 9 | **Llama / Gemma weights** | Source-available with use restrictions, not open source. §7.1 |

**Standing rule:** license is verified at adoption *and* re-verified at each major version bump, recorded in an `ADOPTED-TOOLS.md` with license and verification date. Relicensing happens at major versions, and a stack audit a year from now should not require archaeology.

### 9.1 AGPL — decide once

Several good choices are AGPLv3 (Grafana, Loki, Listmonk, Garage). AGPL's source-disclosure obligation triggers on *modified* software offered over a network. Unmodified self-hosted use is generally fine; the risk is a developer patching Grafana and nobody noticing.

**Recommendation:** permit AGPL tools for internal infrastructure, prohibit them in anything the user's device talks to directly, and add a CI check that flags local patches to AGPL dependencies. Get one written legal opinion covering the whole class rather than litigating it per-tool.

---

## 10. Required PRD changes

| PRD ref | Change |
|---|---|
| §6.1 | Add: no third-party SDKs in client builds. Add F-Droid as an optional Android channel |
| §6.2 | **Strengthen the claim.** "No third-party SDKs; all infrastructure self-hosted and open source" is a materially stronger privacy statement than the current text, and it makes the launch-blocking SDK egress audit trivial |
| §6.3 | Reclassify integrations as Category B data sources. Server-to-server OAuth only; no vendor SDKs embedded |
| §8.1 | Replace "GPT-4o voice with behavioral scripting" with the §7.3 ladder — constrained slot-filling on an Apache-2.0 model, or on-device ASR with templated dialogue |
| §8.8 | Add: MRT randomization is in-house (§6.1); analysis in R/statsmodels; reproducibility via pinned container images referenced in IRB submissions |
| §9 | Add engineering KPI: zero third-party SDKs in shipped client binaries, verified per release |
| §11 | Add risk: **self-hosting operational burden** (§11 below) |
| New §6.4 | Adopted-tools register with licenses and verification dates |

---

## 11. Cost & burden — the honest tradeoff

The constraint is technically satisfiable for everything in Category A. It is not free.

**What it costs:**
- **~1–1.5 FTE of platform/SRE work** from Phase 1 that a Firebase-plus-vendors stack would not require. For a team of the size implied by the PRD roadmap, that is a real feature-velocity tax, and it lands during the phase where §4.4 has to ship.
- ~~Email deliverability~~ — **resolved by D16**, not by an exception. Email is off the critical path, so the remaining volume is receipts and verification links, and a spam-foldered receipt is an annoyance rather than a broken product.
- **Penpot instead of Figma** is a genuine tradeoff for a product whose §7 design principles are load-bearing. Penpot is capable; the ecosystem, plugins, and designer familiarity are not close. This is the constraint's biggest non-obvious cost, and it's a hiring cost as much as a tooling one.
- **Self-hosted LLM inference** is a fixed GPU cost that starts before the revenue does, where an API is usage-priced.

**What it buys, beyond principle:**
- The largest regulatory exposure in PRD §6.2 (SDK exfiltration under the FTC HBNR) mostly disappears.
- WA MHMD's "sale/sharing of consumer health data" analysis becomes short, because there are no third parties in the data path.
- §8.8 reproducibility is IRB-friendly by construction.
- It is a real, checkable differentiator for the privacy-wary 78% in PRD §2 — and unlike most privacy marketing, it survives an audit.

**Net assessment: the constraint is worth taking, with no exceptions.** The one candidate exception (transactional email) dissolved under D16 — the right move was removing email from the critical path rather than outsourcing it, which is both constraint-compliant and a more robust product. Self-host everything.

---

## 12. Decisions — closed

All six are resolved in DECISIONS-v1.

| # | Question | Decision |
|---|---|---|
| 1 | §2 chokepoints | **D15 — accepted on the record.** Xcode, app stores, APNs, FCM-as-transport, StoreKit. External claim is "self-hosted open source infrastructure, no third-party SDKs in the client" |
| 2 | Transactional email | **D16 — no exception taken.** Email removed from the critical path instead (§4.2) |
| 3 | AGPL policy | **D17 — permitted for internal infrastructure**, prohibited in anything the client talks to directly. One legal opinion covering the class; CI check flags local patches to AGPL dependencies |
| 4 | Backend language | **D18 — Python/FastAPI** (§4.1) |
| 5 | Penpot | **D19 — accepted.** Sufficient for this product's needs; the constraint is worth more than the ecosystem gap. Confirm with design leadership before it becomes a hiring constraint, but the default is yes |
| 6 | F-Droid channel | **D19 — yes, Phase 2.** Cheap build variant, serves the privacy-forward segment we are explicitly courting, and it is the only place UnifiedPush works — so it is also our one fully-open push path |

**Nothing in this document is blocked on a decision.**
