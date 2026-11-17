# Architecture and decisions

ShopfloorIQ is a local decision-support demonstration for fictional Northstar Works. Python performs ingestion, validation, metric calculation, anomaly scoring and permission enforcement; SQLite persists source evidence and review state; the browser renders the results.

## Stack evaluation

| Approach | Benefit | Tradeoff / decision |
|---|---|---|
| Streamlit + SQLite | Fast Python-only dashboard development | Repeated app reruns and layout constraints add friction to a persistent multi-step investigation. Not selected. |
| FastAPI + React + SQLite | Rich UI and typed API ecosystem | More installation/build dependencies than this small local workflow needs. Not selected. |
| Python standard-library HTTP + SQLite + buildless browser UI | No third-party dependencies; precise review UX; transparent domain code | Own request validation and UI state; deliberately loopback-only, not a production web platform. Selected. |
| PostgreSQL, containers, orchestration | Multi-user deployments and operational tooling | Unnecessary infrastructure for a laptop demonstration. Not selected. |

No assets, fonts, APIs or telemetry load from external services. `requirements.txt` intentionally contains no packages; Python/SQLite versions come from the installed interpreter. Verified interpreter: Python 3.12.0. Node v24.19.0 ran the developer-only rendering tests.

## Code map

- `generator.py`: seeded source records, labels and a separately retained completion receipt.
- `quality.py`: pure validation rules, timezone-aware parsing, no repair side effects.
- `store.py`: schema, immutable source fingerprinting, atomic refresh, authorization and review commands.
- `analytics.py`: aggregate formulas, filter scope, source drill-down and chronological detector evaluation.
- `investigation.py`: evidence status, complete scoped handover, transparent hold ranking, and audit-derived plans/outcomes.
- `methods.py`: shared robust scoring and a cached, deterministic six-condition stress protocol.
- `server.py`: loopback HTTP, same-origin write checks, static asset allowlist, JSON/CSV and reset.
- `__main__.py`: serve/generate/validate/evaluate/ingest/reset CLI.
- `web/`: semantic HTML shell, responsive CSS, vanilla JavaScript rendering and event handlers.
- `web/experience.js`: evidence-specific views, action forms, handover and stress evaluation; loaded before the main controller.
- `scripts/recording.py`: exclusive creation of a unique recording database, preserving the working file.
- `scripts/verify.py`: isolated automated checks and sanitized results; local database fingerprints stay in ignored logs.
- `scripts/audit_repository.py`, `scripts/verify_clean_export.py`: publication checks of the Git index/history and verification from a clean indexed export.
- `tests/`: domain/HTTP acceptance tests and JavaScript rendering/interaction logic tests.

## Data flow and consistency

1. Generate source objects or accept a bounded JSON array. Validate structural row identity; malformed envelopes reject the entire batch.
2. Serialize each raw row canonically and calculate SHA-256. Re-importing an identical row is a no-op. A different payload at the same `row_id` rejects the whole transaction.
3. Evaluate all raw evidence against the versioned checks. Duplicate `event_id` values are intentionally allowed in staging so all copies can be inspected.
4. Rebuild `findings` and persisted `facts`. Any blocking finding holds the entire affected order. Open, otherwise valid work remains incomplete.
5. Aggregate trusted facts. The API reads facts, investigations and audit under one consistent read transaction.
6. An operator proposes the existing recovery receipt. A different supervisor can approve it. Approval appends one raw row, revalidates, checks the order is clear, updates the proposal and appends audit in one `BEGIN IMMEDIATE` transaction. Any failure rolls back everything.
7. Data resolution is a separate human action. The operational incident is not automatically resolved.

SQLite atomicity is appropriate for this local slice; it makes multi-table updates appear together or not at all. Source: [SQLite atomic commit documentation](https://www.sqlite.org/atomiccommit.html). Concurrent writes are serialized; optimistic incident revisions prevent stale browser decisions from overwriting newer ones. A 20-second SQLite busy timeout handles brief contention; no distributed or high-load claim is made.

## Interface design

The visual system uses forest-green navigation, off-white work surfaces, lime primary emphasis and restrained amber holds. Data trust is distinct from schedule performance. A sticky identity selector and explicit synthetic clock remain visible. Key screens share the same order and incident links.

Mission Control and Order Explorer share period/station/shift filters. Data Trust, Method Lab and system audit clearly use the whole scenario. The incident inbox retains current filter scope but always admits a directly opened incident. A pinned hero card is marked when outside that scope. Drill-down does not silently inherit filters that would hide the selected evidence.

Exports are all trusted orders in the selected period/station/shift, not merely the current paginated/search table. The button says “Export period · trusted.” Charts provide hover titles and a daily-value table. No placeholder interactions, external chart libraries or fake monitoring indicators are required.

## Operational boundary

The HTTP handler is a local demo server, not a hardened internet service. Host allowlisting, loopback bind, CSP, escaped UI text, origin/token checks, bounded imports and server-side permissions reduce avoidable mistakes. They do not provide real authentication. Do not expose the port through a tunnel or deploy this server as-is.

The source database and audit are not cryptographically tamper-evident. Application update guards and hashes protect normal flows; someone with filesystem/SQL access can change the database. Reset is an explicit exception to source retention and is itself audited. Historical review rows remain visible across resets; the system audit contains the reset boundaries.

Structured next steps and closure outcomes use the existing append-only audit payload. This avoids a migration and preserves historical reviews without guessing their meaning. Current plan lookup uses the latest explicit `plan` entry after the latest reset boundary. Closure history remains available after reopening. Read requests do not synthesize or persist new reviews.

## Data model at a glance

| Tables | Responsibility |
|---|---|
| `meta`, `products`, `stations`, `orders` | Scenario clock, master data and planned order cohorts |
| `raw_events`, `checks`, `evidence` | Retained production rows, sampled checks and separate receipts |
| `findings`, `facts` | Recomputed quality findings and analytical facts with evidence state |
| `incidents`, `proposals`, `audit`, `feedback` | Review lifecycle, independent approval, event history and local feedback |

The [data dictionary](data_dictionary.md) documents fields, units and synthetic defects. The public package contains the generator and schema, not a mutable database. First-time startup reconstructs the same seeded source data; review timestamps use the real time of action.

## Verification and delivery

The repository has no bundled third-party runtime code, fonts or icon packages. Python supplies SQLite and HTTP; Node is only a development-test tool. The [CI workflow](../.github/workflows/ci.yml) pins official GitHub Actions to full commit IDs, uses read-only repository permissions and runs isolated tests on Windows/Ubuntu targets. Hosted execution remains unverified until publication. There is no deployment step.
