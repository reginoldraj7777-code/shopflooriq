"""Explicit order-level quarantine. No source record is silently repaired."""
from collections import Counter, defaultdict
from datetime import datetime

VERSION = "dq-1.0"
RULES = {
    "REQUIRED": "Required source fields are present",
    "DUPLICATE": "Event identity occurs exactly once",
    "REFERENCE": "Order and station references agree with master data",
    "TIMESTAMP": "Timestamps include an offset and are not in the future",
    "SEQUENCE": "Steps are unique and ordered start → fill → pack → complete",
    "DURATION": "Completed elapsed time is between 1 minute and 16 hours",
    "FRESHNESS": "Event transfer latency is between 0 and 60 minutes",
    "QUANTITY": "Completed units are whole, positive, and within plan",
    "UNIT": "Production count is measured in each",
    "MISSING_STEP": "Closed orders have all four required steps",
}


def parse(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Timezone offset required")
    return dt


def validate(orders, events, as_of):
    issues = []
    order_map = {o["id"]: o for o in orders}
    ids = Counter(e.get("event_id") for e in events)
    grouped = defaultdict(list)

    def issue(rule, e, detail):
        issues.append(dict(rule=rule, row_id=e.get("row_id", "unknown"), order_id=e.get("order_id"),
                           detail=detail, version=VERSION))

    for e in events:
        grouped[e.get("order_id")].append(e)
        if any(e.get(k) is None or e.get(k) == "" for k in
               ["event_id", "order_id", "station", "kind", "event_time", "ingested_at", "quantity", "unit"]):
            issue("REQUIRED", e, "One or more required fields are absent.")
        if ids[e.get("event_id")] > 1:
            issue("DUPLICATE", e, f"Event {e.get('event_id')} occurs {ids[e.get('event_id')]} times; all copies held.")
        order = order_map.get(e.get("order_id"))
        if not order or e.get("station") != order["station"]:
            issue("REFERENCE", e, "Unknown order or station does not match order routing.")
        try:
            ts, ingested = parse(e["event_time"]), parse(e["ingested_at"])
            if ts > parse(as_of) or ingested > parse(as_of):
                issue("TIMESTAMP", e, "Timestamp is beyond the scenario clock.")
            lag = (ingested - ts).total_seconds() / 60
            if not 0 <= lag <= 60:
                issue("FRESHNESS", e, f"Transfer latency is {lag:.1f} minutes; expected 0–60.")
        except (ValueError, TypeError, KeyError):
            issue("TIMESTAMP", e, "Invalid ISO-8601 timestamp or missing timezone offset.")
        if e.get("unit") != "each":
            issue("UNIT", e, "Expected each; no unit conversion is assumed.")
        q = e.get("quantity")
        if (not isinstance(q, int) or isinstance(q, bool) or q < 0 or
                (e.get("kind") == "complete" and (q == 0 or (order and q > order["planned_units"])))):
            issue("QUANTITY", e, "Count must be an integer within the order plan, and positive at completion.")
    expected = ["start", "fill", "pack", "complete"]
    for o in orders:
        group = grouped[o["id"]]
        anchor = dict(row_id="ORDER-" + o["id"], order_id=o["id"])
        kinds = [e.get("kind") for e in group]
        if o["state"] == "closed" and any(k not in kinds for k in expected):
            issue("MISSING_STEP", anchor, "Closed order lacks: " + ", ".join(k for k in expected if k not in kinds))
        if any(k not in expected for k in kinds) or any(kinds.count(k) > 1 for k in expected):
            issue("SEQUENCE", anchor, "Unknown step or multiple records for the same step.")
        try:
            present = sorted(group, key=lambda e: parse(e["event_time"]))
            sequence = [expected.index(e["kind"]) for e in present]
            if sequence != list(range(len(sequence))):
                issue("SEQUENCE", anchor, "Steps are out of order, repeated, or skip a required preceding step.")
            times = {e["kind"]: parse(e["event_time"]) for e in group}
            if "start" in times and "complete" in times:
                minutes = (times["complete"] - times["start"]).total_seconds() / 60
                if not 1 <= minutes <= 960:
                    issue("DURATION", anchor, f"Elapsed {minutes:.1f} minutes is outside 1–960.")
        except (ValueError, TypeError, KeyError):
            pass  # Timestamp/step rule already explains why the record cannot be ordered.
    return issues
