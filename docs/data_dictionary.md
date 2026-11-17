# Synthetic data dictionary

Seed: **1042**. Scenario clock: **2026-11-15 14:00:00 UTC**. Order starts span **2026-09-05 through 2026-11-15**, inclusive: 72 days, 644 orders, 2,574 initial raw rows, three products and three stations.

## Business entities

| Entity | Key and fields | Semantics |
|---|---|---|
| Product | `id`, `name`, `target_minutes` | SKU-B250 buffer solution 250 mL, 110-min target; SKU-R100 reference reagent 100 mL, 100 min; SKU-K050 laboratory kit 50 units, 90 min. These are fictional packaging descriptions. |
| Station | `id`, `name` | FILL-01 manual filling; PACK-02 primary packaging; PACK-03 kit assembly. A station denotes the accountable work cell for the complete route, not a separate resource for each step. |
| Order | `id`, `station`, `shift`, `product`, `planned_units`, `start`, `due`, `state`, `label` | A closed source order requires evidence for start/fill/pack/complete. `label` is a planted operational-deviation label, never a detector input. Due = planned start + SKU target. |
| Shift | `Early`, `Late`, `Night` | UTC 05:00–13:00, 13:00–21:00, 21:00–05:00. Attributed by planned start; overnight completions remain with their starting order cohort. |
| Quality check | `id`, `order_id`, `observation`, `result`, `sampled_units` | One label-alignment observation per synthetic order; five sampled units. Pass/fail is a check outcome, not counts of defective units. Not a product-release decision. |
| Evidence receipt | `id`, `order_id`, `description`, `event` | BUF-1042 contains a candidate completion retained outside production reporting until approval. |
| Demo user | `alex`, `sam`, `jules`, `robin` | Fictional operator, supervisor, viewer and admin. In-memory identity definitions; deliberately no passwords or real user directory. |

## Raw event schema

| Field | Type | Meaning |
|---|---|---|
| `row_id` | Nonempty string, unique | Ingestion identity. Same identity/same payload is idempotent; changed payload is rejected. |
| `event_id` | String | Business event identity. Duplicates are retained and flagged. |
| `order_id` | String | Reference to order master. Unknown references remain inspectable orphan evidence. |
| `station` | String | Must match the referenced order’s station. |
| `kind` | String | `start`, `fill`, `pack`, `complete`; fill means filling finished, pack means packing started. |
| `event_time` | Offset-bearing ISO-8601 string | Source-observed time; stored as submitted and compared as aware datetime. |
| `ingested_at` | Offset-bearing ISO-8601 string | Synthetic source receipt/transfer time, **not the actual time this application imported it**. Actual import/review time is in audit. |
| `quantity` | Integer | Zero at intermediate milestones; positive completed units within plan at completion. |
| `unit` | String | Must equal `each`. SKU package volumes do not change the count unit. |
| `source` | String | Synthetic source label, usually `synthetic_mes`; hero recovery is `edge_buffer_recovery`. No actual MES integration exists. |

SQLite `raw_events` stores `row_id`, original JSON payload and SHA-256 of canonical JSON. Nullable/wrong-domain fields can enter staging and be flagged. Non-string identifier/timestamp containers, missing row identity and non-JSON numeric values reject the entire batch; the input file remains the submitter’s evidence. JSON export preserves source fields; hashes are in SQLite.

## Analytical and workflow tables

`facts` has one row/order: `order_id`, start `day`, `station`, `shift`, `product`, source `state`, `trust`, `units`, `elapsed`, `wait`, `late`, `due`, `completed`. Held/incomplete rows retain dimensions but have null metric inputs. This is explicit absence of trustworthy measurement, not zero.

`findings`: rule, affected source row/order, detail and rule version. Missing-step/sequence findings can reference `ORDER-<order_id>` because no single raw row captures the problem. Finding count is not a count of distinct bad rows or bad orders. Findings are the current validation view; prior actions are retained in audit, not historical finding snapshots.

`incidents`: ID, order, title, category (`data`/`operational`), state, owner, latest note, revision. `proposals`: linked incident/evidence, proposer/note, pending/approved/rejected state, reviewer and real action times. `audit`: actual UTC time, actor, action, entity, before/after JSON and rule version. `feedback`: time, actor, topic and message.

## Controlled cases

| Order / record | Planted condition | Expected handling |
|---|---|---|
| WO-1042 / INC-1042 | Closed order lacks completion event | Hold all order KPIs; allow reviewed recovery of BUF-1042 |
| WO-1042 / INC-1043 | Fill 06:30 → pack 08:50, a 140-min wait | Separate operational investigation; cause unestablished |
| WO-2630 / R-DUPLICATE-2630 | Duplicate completion event ID | Flag both copies and repeated route step; hold order |
| WO-2631 / E-WO-2631-4 | Count recorded with `kg` unit | Hold; no implicit conversion |
| WO-2632 / E-WO-2632-3 | Pack timestamp precedes preceding steps | Hold timestamp/sequence evidence |
| WO-2628 / E-WO-2628-4 | Negative completion count | Hold impossible quantity |
| WO-2629 / E-WO-2629-2 | Excessive transfer latency | Hold stale evidence |
| WO-OPEN-01 | Starts at 13:00; only start/fill observed | Incomplete, not a missing-step error |

The final rules produce **10 findings across 6 held orders**. Deliberate timing deviations elsewhere are independent of these quality defects. The cadence is simplified to one order per work cell per shift, with only an early-shift cohort on the last scenario day; it is not a capacity simulation.
