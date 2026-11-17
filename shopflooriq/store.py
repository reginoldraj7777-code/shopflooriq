"""SQLite persistence, ingestion, facts and transactional human review."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .generator import generate, HERO
from .quality import validate, parse, VERSION, RULES

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "shopflooriq.sqlite"
USERS = {"alex": {"name": "Alex Morgan", "role": "operator"},
         "sam": {"name": "Sam Chen", "role": "supervisor"},
         "jules": {"name": "Jules Weber", "role": "viewer"},
         "robin": {"name": "Robin Ellis", "role": "admin"}}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path=DEFAULT_DB):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def rows(db, sql, args=()):
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def schema(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS stations(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS raw_events(row_id TEXT PRIMARY KEY,payload TEXT NOT NULL,hash TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS checks(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS findings(id INTEGER PRIMARY KEY,rule TEXT,row_id TEXT,order_id TEXT,detail TEXT,version TEXT);
    CREATE TABLE IF NOT EXISTS facts(order_id TEXT PRIMARY KEY,day TEXT,station TEXT,shift TEXT,product TEXT,
      state TEXT,trust TEXT,units INTEGER,elapsed REAL,wait REAL,late INTEGER,due TEXT,completed TEXT);
    CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY,order_id TEXT,title TEXT,category TEXT,
      state TEXT NOT NULL DEFAULT 'open',owner TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '',version INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS proposals(id INTEGER PRIMARY KEY,incident_id TEXT NOT NULL REFERENCES incidents(id),
      evidence_id TEXT NOT NULL REFERENCES evidence(id),actor TEXT NOT NULL,note TEXT NOT NULL,status TEXT DEFAULT 'pending',
      reviewer TEXT,created TEXT NOT NULL,reviewed TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,
      entity TEXT NOT NULL,before_json TEXT NOT NULL,after_json TEXT NOT NULL,rule_version TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,at TEXT,actor TEXT,category TEXT,message TEXT);
    CREATE INDEX IF NOT EXISTS ix_findings_order ON findings(order_id);
    CREATE TRIGGER IF NOT EXISTS raw_immutable_update BEFORE UPDATE ON raw_events BEGIN SELECT RAISE(ABORT,'Raw events are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS audit_immutable_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'Audit is append only'); END;
    """)


def payloads(db, table):
    if table not in {"products", "stations", "orders", "raw_events", "checks", "evidence"}:
        raise ValueError("Unknown dataset")
    return [json.loads(r[0]) for r in db.execute(f"SELECT payload FROM {table}")]


def meta(db, key):
    return json.loads(db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()[0])


def audit(db, actor, action, entity, before, after):
    db.execute("INSERT INTO audit(at,actor,action,entity,before_json,after_json,rule_version) VALUES(?,?,?,?,?,?,?)",
               (now(), actor, action, entity, json.dumps(before), json.dumps(after), VERSION))


def ingest(db, events):
    added = 0
    for e in events:
        if not isinstance(e, dict) or not isinstance(e.get("row_id"), str) or not e["row_id"].strip():
            raise ValueError("Every staged row needs a nonempty row_id")
        for field in ("event_id", "order_id", "station", "kind", "event_time", "ingested_at", "unit"):
            if e.get(field) is not None and not isinstance(e[field], str):
                raise ValueError(f"{field} must be a string or null; source batch was not committed")
        value = json.dumps(e, sort_keys=True, allow_nan=False)
        digest = hashlib.sha256(value.encode()).hexdigest()
        old = db.execute("SELECT hash FROM raw_events WHERE row_id=?", (e["row_id"],)).fetchone()
        if old and old[0] != digest:
            raise ValueError(f"Immutable row collision: {e['row_id']}")
        if not old:
            db.execute("INSERT INTO raw_events VALUES(?,?,?)", (e["row_id"], value, digest))
            added += 1
    return added


def refresh(db):
    orders, events = payloads(db, "orders"), payloads(db, "raw_events")
    findings = validate(orders, events, meta(db, "as_of"))
    db.execute("DELETE FROM findings")
    db.executemany("INSERT INTO findings(rule,row_id,order_id,detail,version) VALUES(:rule,:row_id,:order_id,:detail,:version)", findings)
    held = {i["order_id"] for i in findings}
    grouped = {}
    for e in events:
        grouped.setdefault(e.get("order_id"), {})[e.get("kind")] = e
    db.execute("DELETE FROM facts")
    for o in orders:
        e = grouped.get(o["id"], {})
        trust = "held" if o["id"] in held else "incomplete" if o["state"] == "open" else "trusted"
        units = elapsed = wait = late = completed = None
        if trust == "trusted":
            completed = e["complete"]["event_time"]
            units = e["complete"]["quantity"]
            elapsed = (parse(completed) - parse(e["start"]["event_time"])).total_seconds() / 60
            wait = (parse(e["pack"]["event_time"]) - parse(e["fill"]["event_time"])).total_seconds() / 60
            late = int(parse(completed) > parse(o["due"]))
        db.execute("INSERT INTO facts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (o["id"], o["start"][:10], o["station"], o["shift"], o["product"], o["state"], trust,
                    units, elapsed, wait, late, o["due"], completed))
    for oid in sorted(held - {None}):
        if not any(o["id"] == oid for o in orders):
            continue
        iid = "INC-1042" if oid == HERO else "DQ-" + oid
        title = "A missing event. A real delay." if oid == HERO else "Production evidence needs review"
        db.execute("INSERT OR IGNORE INTO incidents(id,order_id,title,category) VALUES(?,?,?,?)", (iid, oid, title, "data"))
        incident = dict(db.execute("SELECT * FROM incidents WHERE id=?", (iid,)).fetchone())
        if incident["state"] == "resolved":
            db.execute("UPDATE incidents SET state='open',note='Validation found new blocking evidence; review reopened.',version=version+1 WHERE id=?", (iid,))
            after = dict(db.execute("SELECT * FROM incidents WHERE id=?", (iid,)).fetchone())
            after["findings"] = [f for f in findings if f["order_id"] == oid]
            audit(db, "system", "validation_reopened", iid, incident, after)
    db.execute("INSERT OR IGNORE INTO incidents(id,order_id,title,category) VALUES('INC-1043',?,'Extended fill-to-pack wait','operational')", (HERO,))
    return {"source_rows": len(events), "findings": len(findings), "held_orders": len(held & {o['id'] for o in orders})}


def initialize(path=DEFAULT_DB, seed=1042):
    db = connect(path)
    schema(db)
    if not db.execute("SELECT 1 FROM meta WHERE key='seed'").fetchone():
        data = generate(seed)
        with db:
            for key in ("seed", "as_of"):
                db.execute("INSERT INTO meta VALUES(?,?)", (key, json.dumps(data[key])))
            for table in ("products", "stations", "orders", "checks", "evidence"):
                db.executemany(f"INSERT INTO {table} VALUES(?,?)", [(x["id"], json.dumps(x)) for x in data[table]])
            ingest(db, data["events"])
            refresh(db)
            audit(db, "system", "seed", "scenario", {}, {"seed": seed, "as_of": data["as_of"], "orders": len(data["orders"])})
    return db


def authorize(actor, roles):
    if actor not in USERS or USERS[actor]["role"] not in roles:
        raise PermissionError("This demonstration identity cannot perform that action.")


def command(db, actor, action, body):
    if actor not in USERS:
        raise PermissionError("Unknown demonstration identity")
    with db:
        db.execute("BEGIN IMMEDIATE")
        if action == "refresh":
            authorize(actor, {"admin"})
            result = refresh(db)
            audit(db, actor, action, "pipeline", {}, result)
            return result
        if action == "ingest":
            authorize(actor, {"admin"})
            events = body.get("events")
            if not isinstance(events, list) or not 1 <= len(events) <= 5000:
                raise ValueError("Import 1–5000 event objects")
            for event in events:
                if isinstance(event, dict) and event.get("order_id") == HERO and event.get("kind") == "complete":
                    if not isinstance(event.get("row_id"), str):
                        raise ValueError("Every staged row needs a string row_id")
                    existing = db.execute("SELECT hash FROM raw_events WHERE row_id=?", (event.get("row_id"),)).fetchone()
                    digest = hashlib.sha256(json.dumps(event, sort_keys=True, allow_nan=False).encode()).hexdigest()
                    if existing is None or existing[0] != digest:
                        raise PermissionError("WO-1042 completion requires independently reviewed BUF-1042 recovery; direct import is blocked.")
            count = ingest(db, events)
            result = dict(added=count, **refresh(db))
            audit(db, actor, action, "pipeline", {}, dict(result, row_ids=[e["row_id"] for e in events],
                  batch_sha256=hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest()))
            return result
        if action == "feedback":
            message = str(body.get("message", "")).strip()
            if not 5 <= len(message) <= 2000:
                raise ValueError("Feedback needs 5–2000 characters")
            category = body.get("category", "Usability")
            if category not in ("Usability", "Data explanation", "Workflow issue", "Feature idea"):
                raise ValueError("Unknown feedback topic")
            db.execute("INSERT INTO feedback(at,actor,category,message) VALUES(?,?,?,?)", (now(), actor, category, message))
            audit(db, actor, action, "feedback", {}, {"message": message})
            return {"message": "Feedback recorded"}
        iid = body.get("incident_id")
        if not isinstance(iid, str):
            raise ValueError("incident_id must be a string")
        current = db.execute("SELECT * FROM incidents WHERE id=?", (iid,)).fetchone()
        if current is None:
            raise ValueError("Incident not found")
        before = dict(current)
        extra = {}
        if body.get("version") != before["version"]:
            raise ValueError("This incident changed. Refresh before submitting again.")
        note = str(body.get("note", "")).strip()
        if not 10 <= len(note) <= 2000:
            raise ValueError("Record an evidence-based note of 10–2000 characters.")
        if action == "acknowledge":
            authorize(actor, {"operator", "supervisor", "admin"})
            if before["state"] != "open":
                raise ValueError("Only an open incident can be acknowledged")
            db.execute("UPDATE incidents SET state='acknowledged',owner=?,note=?,version=version+1 WHERE id=?", (actor, note, iid))
        elif action == "note":
            authorize(actor, {"operator", "supervisor", "admin"})
            if before["state"] == "resolved":
                raise ValueError("Reopen an incident before adding work notes")
            db.execute("UPDATE incidents SET note=?,version=version+1 WHERE id=?", (note, iid))
        elif action == "plan":
            from .investigation import meaningful, references, context
            authorize(actor, {"operator", "supervisor", "admin"})
            if before["state"] != "acknowledged":
                raise ValueError("Acknowledge the incident before recording a next step")
            before["plan"] = context(db, iid)["plan"]
            extra["plan"] = dict(next_action=meaningful(body.get("next_action"), "Next investigation step"),
                                 missing_info=meaningful(body.get("missing_info"), "Missing information"),
                                 refs=references(db, before["order_id"], body.get("refs")))
            db.execute("UPDATE incidents SET note=?,version=version+1 WHERE id=?", (note, iid))
        elif action == "propose":
            authorize(actor, {"operator", "supervisor"})
            if iid != "INC-1042" or before["state"] != "acknowledged":
                raise ValueError("Acknowledge the recovery incident before proposing evidence")
            if db.execute("SELECT 1 FROM proposals WHERE incident_id=? AND status IN ('pending','approved')", (iid,)).fetchone():
                raise ValueError("Recovery already proposed or applied")
            db.execute("INSERT INTO proposals(incident_id,evidence_id,actor,note,created) VALUES(?,?,?,?,?)", (iid, "BUF-1042", actor, note, now()))
            db.execute("UPDATE incidents SET note=?,version=version+1 WHERE id=?", (note, iid))
        elif action in {"approve", "reject"}:
            authorize(actor, {"supervisor"})
            proposal = db.execute("SELECT * FROM proposals WHERE incident_id=? AND status='pending'", (iid,)).fetchone()
            if proposal is None:
                raise ValueError("No pending proposal")
            if proposal["actor"] == actor:
                raise PermissionError("A proposer cannot approve or reject their own evidence.")
            if action == "approve":
                evidence = json.loads(db.execute("SELECT payload FROM evidence WHERE id=?", (proposal["evidence_id"],)).fetchone()[0])
                ingest(db, [evidence["event"]])
                refresh(db)
                if db.execute("SELECT 1 FROM findings WHERE order_id=?", (before["order_id"],)).fetchone():
                    raise ValueError("Recovery still fails validation; no changes committed")
            db.execute("UPDATE proposals SET status=?,reviewer=?,reviewed=? WHERE id=?", ("approved" if action == "approve" else "rejected", actor, now(), proposal["id"]))
            db.execute("UPDATE incidents SET note=?,version=version+1 WHERE id=?", (note, iid))
        elif action == "resolve":
            authorize(actor, {"supervisor"})
            if before["state"] != "acknowledged":
                raise ValueError("Acknowledge before resolution")
            if before["category"] == "data" and db.execute("SELECT 1 FROM findings WHERE order_id=?", (before["order_id"],)).fetchone():
                raise ValueError("Blocking data findings remain; resolution is not a data override")
            from .investigation import meaningful, references
            meaningful(note, "Resolution rationale", 40)
            if before["category"] == "operational":
                if body.get("confirm_resolution") is not True:
                    raise ValueError("Explicitly confirm operational closure after reviewing the evidence and remaining uncertainty")
                outcome = body.get("outcome")
                if outcome not in {"mitigated", "administratively_closed"}:
                    raise ValueError("Choose mitigated or administratively closed. This workflow cannot verify a root cause.")
                extra["resolution"] = dict(outcome=outcome, cause_status="not_established",
                    uncertainty=meaningful(body.get("uncertainty"), "Remaining uncertainty"),
                    refs=references(db, before["order_id"], body.get("refs")))
                if outcome == "mitigated":
                    extra["resolution"]["action_taken"] = meaningful(body.get("action_taken"), "Recorded mitigation and verification")
                else:
                    extra["resolution"]["action_taken"] = "No mitigation asserted by this closure."
            db.execute("UPDATE incidents SET state='resolved',note=?,version=version+1 WHERE id=?", (note, iid))
        elif action == "reopen":
            authorize(actor, {"supervisor", "admin"})
            if before["state"] != "resolved":
                raise ValueError("Only resolved incidents may be reopened")
            db.execute("UPDATE incidents SET state='open',note=?,version=version+1 WHERE id=?", (note, iid))
        else:
            raise ValueError("Unknown action")
        after = dict(db.execute("SELECT * FROM incidents WHERE id=?", (iid,)).fetchone())
        after.update(extra)
        after["review_note"] = note
        if action in {"propose", "approve", "reject"}:
            after["proposal"] = dict(db.execute("SELECT * FROM proposals WHERE incident_id=? ORDER BY id DESC LIMIT 1", (iid,)).fetchone())
        audit(db, actor, action, iid, before, after)
        return after
