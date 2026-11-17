# Quality, review and governance

## Rules: dq-1.0

Every finding blocks its affected order. Orphan rows are retained but cannot enter an order KPI.

| Rule | Check |
|---|---|
| REQUIRED | Event ID, order, station, step, event/receipt time, quantity and unit are present |
| DUPLICATE | Event ID occurs once; every copy is flagged when repeated |
| REFERENCE | Known order and matching station routing |
| TIMESTAMP | Parseable offset-aware time, not after the fixed scenario clock |
| SEQUENCE | Known unique route steps in chronological prefix order, without skipped predecessors |
| DURATION | Start-to-complete elapsed time between 1 and 960 minutes inclusive |
| FRESHNESS | Synthetic receipt minus observation between 0 and 60 minutes inclusive |
| QUANTITY | Integer, not boolean, nonnegative; completion positive and no greater than plan |
| UNIT | `each`, with no automatic conversions |
| MISSING_STEP | A closed order has all four milestones; open prefixes are not automatically errors |

Freshness is transfer latency relative to a fixed demonstration clock. It is not wall-clock live monitoring or proof of source uptime. Separate negative fixtures exercise every rule, unknown foreign keys, malformed timestamps, offsets, future events, invalid quantities and incorrect ordering.

## Role matrix

| Action | Viewer Jules | Operator Alex | Supervisor Sam | Admin Robin |
|---|:---:|:---:|:---:|:---:|
| Read, inspect, export | ✓ | ✓ | ✓ | ✓ |
| Submit local feedback | ✓ | ✓ | ✓ | ✓ |
| Acknowledge / own / annotate | — | ✓ | ✓ | ✓ |
| Record next investigation step | — | ✓ | ✓ | ✓ |
| Propose recovery | — | ✓ | ✓ | — |
| Approve / reject another proposer | — | — | ✓ | — |
| Resolve | — | — | ✓ | — |
| Reopen | — | — | ✓ | ✓ |
| Ingest / refresh / reset | — | — | — | ✓ |

These are freely selected **demo identities, not authenticated people**. Permissions and actor separation are enforced in Python, not merely hidden by UI styling. There is only one seeded supervisor: if Sam proposes the receipt, Sam cannot approve it. For the guided path, Alex proposes and Sam reviews. If a rehearsal is placed in an unreviewable self-proposal state, start a separate recording database; preserve the original review history. Real deployments would need managed identities and multiple approvers.

## State changes

`open → acknowledged → resolved → open`

- Acknowledge sets the owner to the acting identity and records a note.
- Annotation and proposal require an acknowledged/open work context as enforced by the command handler; proposals specifically require acknowledged INC-1042.
- Approval/rejection requires a pending proposal, supervisor role and a different actor from its proposer.
- Approval appends the preserved candidate row and validates it. Remaining findings roll back the whole approval.
- Admin source import cannot introduce a new hero completion and bypass this review; after approval, exact reimports remain idempotent.
- Resolution requires an acknowledged incident. A data incident additionally requires no current findings; a note never overrides a hold.
- All resolutions require 40–2,000 characters and at least six distinct words, in addition to supervisor role and acknowledged state.
- Operational resolution also requires explicit confirmation, a known outcome (`mitigated` or `administratively_closed`), at least one existing source-row/check reference from the same order, and 30+ characters / six distinct words documenting remaining uncertainty. A mitigation also requires an action-and-verification statement of the same minimum length. These structural checks cannot judge the truth of a person's account.
- Cause status is explicitly `not_established`. This slice does not have the independent causal evidence workflow needed to verify a root cause; it therefore does not offer a root-cause-confirmed outcome. Administrative closure makes no mitigation claim. The guided demo leaves INC-1043 open.
- Structured plans require acknowledged state, a next step and missing-information statement (each 30–2,000 characters / six distinct words), and valid evidence references. The selected incident's owner remains responsible; the author and actual action time are audited. Plans are intentions, not completed corrective actions.
- Reopening preserves recovered source evidence and previous actions.
- New blocking evidence automatically reopens a resolved data incident once, with a system audit record; repeated validation does not create repeated reopening events.
- Every incident write requires the revision the browser inspected; stale submissions fail with a refresh instruction.

Notes require 10–2,000 characters. Feedback requires 5–2,000. Actual action timestamps use UTC independently of synthetic event time. Audit records include actor, action, entity, rule version and before/after payload; proposals additionally record source receipt, proposer and reviewer. Imports record row identities and batch fingerprint.

## Data-quality release versus product release

This app approves an **evidence recovery for analytics**, not a product-quality release. It has no product-release decision, manufacturing authorization or regulatory signature. No one, including an admin, can self-approve the modeled recovery. Sampled check outcomes remain observations.

## Retention and lifecycle

Raw rows cannot be updated through the app; identical reimports are no-ops and collisions fail atomically. New source defects recompute holds. Source hashes and audit before/after entries support inspection but are not a certified, tamper-evident records system.

The destructive reset control was removed from the UI. Use `Start-Recording.cmd` to create a separate database for each rehearsal. The legacy admin-only reset API/CLI remains for explicitly disposable test databases; it clears current production/review state while retaining audit and feedback and appending `scenario_reset`. Never use it on the preserved working database without explicit permission. Current structured plans ignore audit entries before a reset boundary. Incident audit shows only the selected incident; related investigations have separate links. The system audit shows the most recent 200 entries; SQLite retains all entries.

Plans and closure outcomes live in additional JSON fields on new audit entries, using the existing transactional command path. No schema migration, historical rewrite, fabricated backfill or deletion is needed. Prior review notes are displayed verbatim, without silently parsing them into asserted completed actions.

The modeled use-case lifecycle is: signal identification → owner acknowledgment → evidence investigation → proposed analytics correction → independent validation → documented disposition → audit/reopen. There is no portfolio approval workflow, SLA escalation or ticketing integration.

## Transport boundary

Loopback-only listener, allowed hostnames, same-origin write checks, random per-server CSRF token, static-file allowlist, escaped text and restrictive CSP. These controls are tested. They do not make the freely selectable identities secure authentication. Local CLI commands intentionally act as the synthetic admin. Filesystem access is outside the app permission model.
