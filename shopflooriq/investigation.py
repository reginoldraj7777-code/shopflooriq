"""Evidence-linked work plans, read from the existing append-only audit log.

No schema migration or reinterpretation of historical free-text reviews is needed.
Plans are human-recorded intentions, never evidence that an action was performed.
"""
import json
import re
from .store import rows, payloads


def meaningful(value, label, minimum=30):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= 2000 or len(set(re.findall(r"\w+", value.lower()))) < 6:
        raise ValueError(f"{label} needs {minimum}–2000 characters and at least six distinct words.")
    return value.strip()


def references(db, order_id, value):
    valid = {r["row_id"] for r in payloads(db, "raw_events") if r.get("order_id") == order_id}
    valid |= {r["id"] for r in payloads(db, "checks") if r.get("order_id") == order_id}
    if not isinstance(value, list) or not value or len(value) > 20 or any(not isinstance(v, str) or v not in valid for v in value):
        raise ValueError("Select at least one existing source row or check belonging to this order (maximum 20).")
    return list(dict.fromkeys(value))


def context(db, incident_id):
    # Resets retain historical audit. Do not carry an old plan into a fresh scenario.
    cutoff = db.execute("SELECT COALESCE(MAX(id),0) FROM audit WHERE action='scenario_reset'").fetchone()[0]
    history = rows(db, "SELECT * FROM audit WHERE entity=? AND id>? ORDER BY id DESC", (incident_id, cutoff))
    result = {"plan": None, "resolution": None}
    for entry in history:
        after = json.loads(entry["after_json"])
        for key in result:
            if result[key] is None and key in after:
                result[key] = dict(after[key], actor=entry["actor"], at=entry["at"], audit_id=entry["id"])
    return result


def evidence_steps(order, events, findings, proposals):
    approved = any(p["status"] == "approved" for p in proposals)
    steps = []
    for kind in ("start", "fill", "pack", "complete"):
        records = [v for v in events if v.get("kind") == kind]
        row_ids = {v["row_id"] for v in records}
        direct = [f for f in findings if f["row_id"] in row_ids]
        if not records:
            status = "Not yet observed" if order["state"] == "open" else "Missing event"
        elif findings:
            status = "Evidence held"  # Even locally clean rows cannot validate a held order.
        elif approved and any(v.get("source") == "edge_buffer_recovery" or v["row_id"] == "R-RECOVERY-1042" for v in records):
            status = "Recovered · approved"
        elif order["state"] == "open":
            status = "Recorded · prefix checked"
        else:
            status = "Validated"
        steps.append(dict(kind=kind, status=status, events=records, findings=direct,
                          order_held=bool(findings)))
    return steps


def trust_impact(facts, orders, findings):
    planned = {o["id"]: o["planned_units"] for o in orders}
    held = []
    for f in facts:
        if f["trust"] != "held":
            continue
        issues = [v for v in findings if v["order_id"] == f["order_id"]]
        held.append(dict(order_id=f["order_id"], station=f["station"], shift=f["shift"],
                         planned_units=planned[f["order_id"]], excluded_orders=1,
                         rules=sorted({v["rule"] for v in issues}), findings=len(issues)))
    return sorted(held, key=lambda h: (-h["planned_units"], h["order_id"]))


def handover(db, facts, incidents, findings, filters):
    orders = payloads(db, "orders")
    events = payloads(db, "raw_events")
    items = []
    for incident in incidents:
        if incident["state"] == "resolved":
            continue
        oid = incident["order_id"]
        fact = next(f for f in facts if f["order_id"] == oid)
        refs = [v["row_id"] for v in events if v.get("order_id") == oid]
        items.append(dict(incident, **context(db, incident["id"]), refs=refs,
                          trust=fact["trust"], station=fact["station"], shift=fact["shift"]))
    held = trust_impact(facts, orders, findings)
    rank = {h["order_id"]: index for index, h in enumerate(held)}
    operational = sorted([i for i in items if i["category"] == "operational"], key=lambda i: i["id"])
    data = sorted([i for i in items if i["category"] == "data"], key=lambda i: (rank.get(i["order_id"], len(held)), i["id"]))
    total = db.execute("SELECT COUNT(*) FROM incidents WHERE state!='resolved'").fetchone()[0]
    return dict(scope=dict(filters), operational=operational, data=data, held=held,
                outside_scope=total-len(items), open_count=len(items),
                ranking="Operational investigations first (incident ID order); data holds by planned units descending, then order ID. Planned units indicate reporting exposure, not actual loss or recoverable output.")
