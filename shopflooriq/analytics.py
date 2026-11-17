"""Reconciled metrics and explainable, held-out anomaly comparison."""
from collections import defaultdict
from statistics import median
from datetime import date
from .store import rows, payloads, meta, USERS
from .quality import RULES, parse, VERSION
from .generator import HERO
from .investigation import context, evidence_steps, trust_impact, handover
from .methods import score, stress_evaluation


def aggregate(facts, checks):
    trusted = [f for f in facts if f["trust"] == "trusted"]
    ids = {f["order_id"] for f in trusted}
    observed = [q for q in checks if q["order_id"] in ids]
    closed = sum(f["state"] == "closed" for f in facts)
    return dict(orders=len(facts), closed=closed, completed=len(trusted), held=sum(f["trust"] == "held" for f in facts),
                incomplete=sum(f["trust"] == "incomplete" for f in facts), units=sum(f["units"] for f in trusted),
                elapsed=round(sum(f["elapsed"] for f in trusted) / len(trusted), 1) if trusted else None,
                late_count=sum(f["late"] for f in trusted), late_share=round(100 * sum(f["late"] for f in trusted) / len(trusted), 1) if trusted else None,
                coverage=round(100 * len(trusted) / closed, 1) if closed else None,
                checks=len(observed), passed_checks=sum(q["result"] == "pass" for q in observed),
                check_rate=round(100 * sum(q["result"] == "pass" for q in observed) / len(observed), 1) if observed else None)


def method_lab(facts, orders):
    labels = {o["id"]: o["label"] for o in orders}
    trusted = [f for f in facts if f["trust"] == "trusted"]
    train = [f for f in trusted if f["day"] < "2026-10-23"]
    test = [f for f in trusted if f["day"] >= "2026-10-23"]
    baselines = {}
    for station in sorted({f["station"] for f in train}):
        values = [f["wait"] for f in train if f["station"] == station]
        center = median(values)
        mad = median(abs(v - center) for v in values)
        baselines[station] = dict(median=center, mad=mad, n=len(values))
    scored = []
    for f in test:
        b = baselines.get(f["station"])
        if not b or b["n"] < 20:
            scored.append(dict(order_id=f["order_id"], station=f["station"], wait=f["wait"], score=None,
                               rule=f["wait"] > 60, robust=None, label=labels[f["order_id"]]))
            continue
        # Zero MAD: exact center is zero, any departure is explicitly flagged.
        z = score(f["wait"], b)
        scored.append(dict(order_id=f["order_id"], station=f["station"], wait=f["wait"], score=round(z, 2),
                           rule=f["wait"] > 60, robust=z > 3.5, label=labels[f["order_id"]]))
    methods = []
    for key, name in [("rule", "Fixed wait threshold"), ("robust", "Station-aware median / MAD")]:
        available = [s for s in scored if s[key] is not None]
        tp = sum(s[key] and s["label"] for s in available)
        fp = sum(s[key] and not s["label"] for s in available)
        fn = sum(not s[key] and s["label"] for s in available)
        tn = sum(not s[key] and not s["label"] for s in available)
        methods.append(dict(name=name, key=key, tp=tp, fp=fp, fn=fn, tn=tn,
                            evaluated=len(available), unavailable=len(scored)-len(available),
                            precision=round(tp / (tp + fp), 3) if tp + fp else None,
                            recall=round(tp / (tp + fn), 3) if tp + fn else None))
    return dict(methods=methods, training=len(train), testing=len(test), baselines=baselines,
                positives=sum(s["label"] for s in scored), signals=sorted(scored, key=lambda s: s["score"] if s["score"] is not None else -1e9, reverse=True),
                excluded=sum(f["trust"] != "trusted" for f in facts), split="2026-10-23", stress=stress_evaluation())


def snapshot(db, filters=None):
    filters = filters or {}
    for key in ("from", "to"):
        if filters.get(key):
            try:
                if date.fromisoformat(filters[key]).isoformat() != filters[key]:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError("Date filters must use YYYY-MM-DD") from None
    if filters.get("from") and filters.get("to") and filters["from"] > filters["to"]:
        raise ValueError("From date must be on or before to date")
    all_facts = rows(db, "SELECT * FROM facts ORDER BY day DESC,order_id")
    facts = [f for f in all_facts if (not filters.get("station") or f["station"] == filters["station"])
             and (not filters.get("shift") or f["shift"] == filters["shift"])
             and (not filters.get("from") or f["day"] >= filters["from"])
             and (not filters.get("to") or f["day"] <= filters["to"])]
    checks = payloads(db, "checks")
    grouped = defaultdict(list)
    for f in facts:
        grouped[f["day"]].append(f)
    trend = [dict(day=d, **aggregate(grouped[d], checks)) for d in sorted(grouped)]
    ids = {f["order_id"] for f in facts}
    findings = rows(db, "SELECT * FROM findings ORDER BY order_id,rule,row_id")
    lab = method_lab(all_facts, payloads(db, "orders"))
    incidents = [i for i in rows(db, "SELECT * FROM incidents ORDER BY CASE WHEN id='INC-1042' THEN 0 ELSE 1 END,id") if i["order_id"] in ids]
    return dict(as_of=meta(db, "as_of"), seed=meta(db, "seed"), version=VERSION, users=USERS,
                products=payloads(db, "products"), stations=payloads(db, "stations"),
                metrics=aggregate(facts, checks), facts=facts, trend=trend,
                featured_incident=rows(db, "SELECT * FROM incidents WHERE id='INC-1042'")[0],
                featured_fact=next(f for f in all_facts if f["order_id"] == HERO),
                featured_recovery_approved=bool(db.execute("SELECT 1 FROM proposals WHERE incident_id='INC-1042' AND status='approved'").fetchone()),
                station_metrics=[dict(station=s["id"], name=s["name"], **aggregate([f for f in facts if f["station"] == s["id"]], checks)) for s in payloads(db, "stations")],
                incidents=incidents, handover=handover(db, facts, incidents, findings, filters),
                trust_impact=trust_impact(all_facts, payloads(db, "orders"), findings),
                global_metrics=aggregate(all_facts, checks),
                findings=findings, rules=[dict(id=k, name=v, count=sum(i["rule"] == k for i in findings)) for k,v in RULES.items()],
                source_rows=db.execute("SELECT count(*) FROM raw_events").fetchone()[0],
                all_order_ids=[f["order_id"] for f in all_facts],
                orphan_events=[v for v in payloads(db, "raw_events") if v.get("order_id") not in {f["order_id"] for f in all_facts}],
                audit=rows(db, "SELECT * FROM audit ORDER BY id DESC LIMIT 200"),
                feedback=rows(db, "SELECT * FROM feedback ORDER BY id DESC"), lab=lab)


def order_detail(db, oid):
    order = next((o for o in payloads(db, "orders") if o["id"] == oid), None)
    if order is None:
        raise ValueError("Order not found")
    events = [e for e in payloads(db, "raw_events") if e.get("order_id") == oid]
    findings = rows(db, "SELECT * FROM findings WHERE order_id=?", (oid,))
    fact = rows(db, "SELECT * FROM facts WHERE order_id=?", (oid,))[0]
    evidence = [e for e in payloads(db, "evidence") if e["order_id"] == oid]
    naive_elapsed = (parse(meta(db, "as_of")) - parse(order["start"])).total_seconds() / 60
    preview = None
    if evidence:
        candidate = evidence[0]["event"]
        preview = dict(units=candidate["quantity"], elapsed=(parse(candidate["event_time"]) - parse(order["start"])).total_seconds() / 60,
                       late=parse(candidate["event_time"]) > parse(order["due"]),
                       naive_elapsed=naive_elapsed, evidence_id=evidence[0]["id"], current_trust=fact["trust"],
                       applied=bool(db.execute("SELECT 1 FROM proposals WHERE evidence_id=? AND status='approved'",(evidence[0]["id"],)).fetchone()))
    incidents = rows(db, "SELECT * FROM incidents WHERE order_id=? ORDER BY id", (oid,))
    for incident in incidents:
        incident.update(context(db, incident["id"]))
    proposals = rows(db, "SELECT p.* FROM proposals p JOIN incidents i ON i.id=p.incident_id WHERE i.order_id=? ORDER BY p.id", (oid,))
    return dict(order=order, fact=fact, events=events, findings=findings, evidence=evidence, preview=preview,
                steps=evidence_steps(order, events, findings, proposals),
                checks=[c for c in payloads(db, "checks") if c["order_id"] == oid], incidents=incidents,
                proposals=proposals,
                audit=rows(db, "SELECT a.* FROM audit a JOIN incidents i ON i.id=a.entity WHERE i.order_id=? ORDER BY a.id DESC", (oid,)))
