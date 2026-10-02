# RITUAL backend

Python 3.13. Implements [SPEC-habit-engine-v1](../SPEC-habit-engine-v1.md),
[SPEC-failure-layer-v1](../SPEC-failure-layer-v1.md) and the Sleep Reset
titration from [SPEC-journeys-v1](../SPEC-journeys-v1.md) §5.3.

## Layout

Two packages, and the dependency runs one way only.

```
ritual/            domain core — framework-free, stdlib only
  engine/
    models.py      core types (§1)
    scheduling.py  occurrence generation in local wall clock (§4)
    stability.py   cue-stability scoring, circular statistics (§3)
    fading.py      fade ladder, probe days, attribution (§5, §6)
    states.py      lapse transitions, recovery surfacing (D1)
  journeys/
    sleep.py       window titration with the 5.5h floor

src/               application layer — imports ritual, never the reverse
  habits/          routers, SQLAlchemy models, stability adapter
  failure_layer/   state machine, service, persistence
  occurrences/     materialisation
  plans/           WOOP and if-then plans
  instruments/     SRBAI, WHO-5, MCTQ, BREQ-3, PSS-10
  notifications/   APNs (direct), FCM (transport only)
  workers/         Celery tasks
  core/            config, database, Kratos
```

**`ritual` must never import from `src`.** That constraint is what keeps the
rules testable without Postgres, FastAPI, or a running clock — which is why a
suite this specific runs in milliseconds.

## Run the tests

```powershell
cd backend
python -m unittest discover -s tests -t .
```

The domain suite (`tests/test_engine.py`, `test_states.py`, `test_sleep.py`) is
**105 tests, stdlib only, no dependencies**. The pytest suites in `tests/unit/`
and `tests/integration/` need the dev extras:

```powershell
uv sync --extra dev
```

## Implemented

| Spec | Status |
|---|---|
| Engine §1 object model | Done |
| Engine §3 cue-stability scoring | Done — circular stats, weakest-dimension reporting, class priors |
| Engine §4 scheduling, DST, travel | Done |
| Engine §5 fade ladder, probe days | Done — all five fences |
| Engine §6 unprompted attribution | Done — delivery-time governed |
| Failure layer §2 state machine | Done — transitions, counters, D1 push/pull |
| Failure layer §9.1 bad week | Done |
| Engine §7 stacking / chains | Done — head-only prompting, cap of 3, anchor-stability gate |
| Engine §9 graduation | Done — three criteria, SRBAI cadence, maintenance checks, the message |
| Journeys §5.3 sleep titration | Done — floor, sleepiness override, no imputation |
| Persistence, HTTP, workers | Booting. App serves, schema builds, 13 API endpoints mounted |

## Not yet implemented

| Spec | Notes |
|---|---|
| Failure layer §4 copy deck | Blocked on copy review (PLAN §1) |
| Journeys | Content blocked on clinician contracting |
| Alembic migration | Schema has changed (`graduated_at`, `prompt_delivered_at`, `srbai_measurements`); no migration generated yet — `versions/` is still empty |
| SRBAI collection | Storage and the graduation evaluator exist; nothing yet *asks* the four questions on the biweekly cadence |

## Wiring note (25 Aug 2026)

Chains and graduation are now connected to the application layer, and three
further defects surfaced while doing it.

1. **Fade advancement ignored misses.** `fade_evaluation` loaded the last three
   *completed* occurrences and checked they were unprompted, which is not the
   same as three *consecutive* unprompted completions (§5.2). A habit going
   complete-miss-complete-miss-complete advanced a level — fading someone's
   prompts down at the moment their record says they still need them. Now
   delegates to `should_advance`, and queries unfiltered by outcome so the
   rule can see what broke the streak.
2. **Undelivered prompts were scored as prompted.** `compute_unprompted` used
   `prompt_delivered_at or prompt_sent_at`, so a prompt sent at 07:00 and never
   delivered made an 08:15 completion "prompted" — inverting §6.1 for exactly
   the users whose phones are least reliable, and understating the primary
   success metric. Both callers now share `ritual.engine.fading.unprompted_at`.
3. **Delivery time was never persisted.** It was a function argument to
   `complete_occurrence` and discarded, leaving `unprompted` a derived boolean
   whose input no longer existed — unauditable and impossible to recompute if
   the rule changed. Added `occurrences.prompt_delivered_at`.

Chains use the existing implicit representation (habits sharing an anchor,
ordered by `Habit.chain_position`) rather than new tables. `src/habits/chains.py`
assembles them for the core's predicates; suppression is applied at occurrence
generation so probe assignment cannot later pick a tail link and "withhold" a
prompt that was never going to be sent.

## Merge note (8 Aug 2026)

`src/` and `ritual/` were built in parallel and duplicated four modules. Per the
reconciliation decision, `src/` is now the application layer and delegates the
rules to `ritual/`. Three defects were fixed in the process:

1. **DST gap handling** (`workers/tasks/occurrence_generation.py`). The pytz
   `is_dst=True` fallback moved a gap-hour occurrence an hour *earlier* rather
   than forward — into the quiet window. Now uses `ritual.engine.scheduling.
   resolve_local`, which shifts forward through gaps and takes the first instant
   of an ambiguous hour.
2. **Recovery push flag** (`failure_layer/state_machine.py`). `lapsed_2` set
   `push_side_trigger=True`, but SPEC-failure-layer §3.1 forbids delivering
   recovery content by push at *any* depth. Now False everywhere.
3. **Probe fences 3 and 5** (`workers/tasks/probe_assignment.py`) were declared
   in the docstring but unimplemented — selection was uniform random over all
   prompted occurrences, so a user could be probed on the same weekday
   indefinitely. Both now enforced, with limits imported from the core.

Also dropped `pytz` and `numpy`: `zoneinfo` and ten lines of `math` cover both
uses, and `pytz` is the superseded API. Two stability boundary conditions were
corrected to match the §3.1 table (a MAD of exactly 75 is *variable*, a
locational share of exactly 0.75 is *variable*), which additionally required
rounding the MAD — the trigonometric round trip returns 75.000000000000014 for
a genuine 75-minute spread.

`tests/test_engine.py::TestApplicationAdapter` guards the merge: if `src/`
drifts from the core, or starts dragging FastAPI into the core's test path, it
fails.

## First boot (8 Aug 2026)

`src/` had never been executed. Getting it running surfaced four further
defects, all of which would have blocked the first developer to try:

1. **`occurrences` was missing from `Base.metadata`.** It is the one package
   with no router, so nothing imported its models outside `alembic/env.py`, and
   `misses.scheduled_occurrence_id -> occurrences.id` failed to resolve on any
   `create_all`. Fixed with a single registry, `src/models.py`, imported by both
   the app and Alembic so the two cannot disagree.
2. **`JSONB` cannot be rendered by the SQLite compiler**, so the whole schema
   was uncreatable under the in-memory database the integration test uses. Now
   `JSON().with_variant(JSONB, "postgresql")` — Postgres keeps JSONB.
3. **Circular foreign key** between `habits.plan_id` and `plans.habit_id` with
   no `use_alter`, which stalls table ordering for both `create_all` and
   migrations. Broken on `habits.plan_id`, the convenience pointer.
4. **`pydantic[email]` was undeclared** while `src/users/schemas.py` uses
   `EmailStr`, which raises at schema-build time. Added, along with `aiosqlite`
   in the dev extras.

Verified after the fixes:

```
pytest tests/unit tests/integration   ->  60 passed
unittest domain suite                  -> 105 passed
GET /health                            -> 200
GET /openapi.json                      -> 200, 9 API paths + /health
Base.metadata                          -> 10 tables
```

One test assertion was corrected rather than the code:
`test_lapsed_2_triggers_recovery_break` asserted `push_side_trigger is True`,
which contradicts §3.1. It now asserts the opposite, with the reasoning inline,
plus a companion test that no transition anywhere sets a push trigger.

## Conflict detection round (25 Aug 2026)

Goal-conflict detection (Engine §8) arrived with two failing tests. Four causes:

1. **`app.dependency_overrides` assigned at module import** in both integration
   modules. Import order then decided which engine the app talked to, so one
   module created its schema on engine A while requests read engine B —
   surfacing as `no such table: users`, which looks like a migration fault and
   is not one. Overrides are now applied and removed per test.
2. **In-memory SQLite hands out a new empty database per connection.** Both
   modules now pin to one via `StaticPool`, so the schema they create is the
   schema the handler sees.
3. **Route ordering.** `GET /habits/{habit_id}` was declared before
   `GET /habits/conflicts`, so "conflicts" bound to `habit_id`, failed UUID
   validation, and returned 422 without ever reaching the handler. Static
   routes now precede the catch-all, with a comment saying why.
4. **A `db_session` fixture that did not exist.** `tests/unit/
   test_conflict_detection.py` asked for one — its own comment says "we should
   refactor the task to take a session for testing". It is now provided in
   `conftest.py`. **That test body is still a stub ending in `pass`; it asserts
   nothing.** Left as-is: it is in-flight work, not something to silently
   finish.

Also: `src/core/types.py` now holds the portable column types. `postgresql.UUID`
and `JSONB` are correct for production and unusable on the SQLite test
database — `Uuid` emits native UUID on Postgres and a round-tripping CHAR(32)
elsewhere, and `JSON_TYPE` varies to JSONB only on Postgres. Import column types
from there, not from a dialect module.

### Note for whoever owns `alembic/env.py`

It currently imports the registry *and* re-lists four model modules explicitly.
The explicit list is now an incomplete subset — `occurrences`, `failure_layer`
and `notifications` are missing from it. Nothing breaks, because
`from src.models import Base` pulls all of them in first, but the partial list
reads as authoritative and is the exact drift the registry exists to prevent.
Worth deleting those four lines.
