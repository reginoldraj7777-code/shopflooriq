"""Executable acceptance tests. All writes stay in disposable workspace databases."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from shopflooriq.generator import generate, AS_OF, HERO
from shopflooriq.quality import validate, parse, RULES
from shopflooriq.store import initialize, rows, payloads, ingest, refresh, command, ROOT
from shopflooriq.analytics import snapshot, order_detail, aggregate, method_lab
from shopflooriq.server import Server, reset

TEST_ROOT = ROOT / "test-results"
TEST_ROOT.mkdir(exist_ok=True)


class GeneratorTests(unittest.TestCase):
    def test_deterministic_seed(self):
        self.assertEqual(generate(), generate())
        self.assertNotEqual(generate(9)["events"], generate(10)["events"])

    def test_relationships_and_size(self):
        d = generate()
        self.assertEqual(len(d["orders"]), 644)
        self.assertEqual(len(d["events"]), 2574)
        self.assertEqual(len({o["start"][:10] for o in d["orders"]}), 72)
        order_ids = {o["id"] for o in d["orders"]}
        self.assertTrue(all(v["order_id"] in order_ids for v in d["events"] + d["checks"]))
        self.assertEqual(len({e["row_id"] for e in d["events"]}), len(d["events"]))
        self.assertTrue(all(o["product"] in {p["id"] for p in d["products"]} for o in d["orders"]))
        self.assertTrue(all(parse(e["ingested_at"]) <= parse(AS_OF) for e in d["events"]))

    def test_hero_receipt_is_not_in_production_source(self):
        d = generate()
        self.assertNotIn("R-RECOVERY-1042", {e["row_id"] for e in d["events"]})
        self.assertEqual(d["evidence"][0]["event"]["quantity"], 720)


class QualityTests(unittest.TestCase):
    def setUp(self):
        d = generate()
        self.order = d["orders"][0]
        self.events = [e for e in d["events"] if e["order_id"] == self.order["id"]]

    def codes(self):
        return {f["rule"] for f in validate([self.order], self.events, AS_OF)}

    def test_clean_control(self):
        self.assertEqual(self.codes(), set())

    def test_required(self):
        self.events[1].pop("unit")
        self.assertIn("REQUIRED", self.codes())

    def test_duplicate_all_copies_flagged(self):
        self.events.append(dict(self.events[0], row_id="another"))
        findings = validate([self.order], self.events, AS_OF)
        self.assertEqual(sum(f["rule"] == "DUPLICATE" for f in findings), 2)

    def test_unknown_order(self):
        self.events[0]["order_id"] = "UNKNOWN"
        self.assertIn("REFERENCE", self.codes())

    def test_station_mismatch(self):
        self.events[0]["station"] = "UNKNOWN"
        self.assertIn("REFERENCE", self.codes())

    def test_timestamp_no_offset(self):
        self.events[0]["event_time"] = "2026-09-05T05:00:00"
        self.assertIn("TIMESTAMP", self.codes())

    def test_timestamp_bad_string(self):
        self.events[0]["event_time"] = "invalid"
        self.assertIn("TIMESTAMP", self.codes())

    def test_future_timestamp(self):
        self.events[-1]["event_time"] = "2026-12-01T00:00:00+00:00"
        self.assertIn("TIMESTAMP", self.codes())

    def test_timezone_equivalence(self):
        self.events[0]["event_time"] = "2026-09-05T07:00:00+02:00"
        self.assertEqual(self.codes(), set())

    def test_sequence_reversed(self):
        self.events[1]["event_time"] = self.events[3]["event_time"]
        self.assertIn("SEQUENCE", self.codes())

    def test_open_prefix_gap(self):
        self.order["state"] = "open"
        self.events = [self.events[0], self.events[2]]
        self.assertIn("SEQUENCE", self.codes())

    def test_unknown_step(self):
        self.events[1]["kind"] = "mystery"
        self.assertIn("SEQUENCE", self.codes())

    def test_duration_too_long(self):
        self.events[-1]["event_time"] = "2026-09-06T05:00:00+00:00"
        self.assertIn("DURATION", self.codes())

    def test_duration_negative(self):
        self.events[-1]["event_time"] = "2026-09-05T04:00:00+00:00"
        self.assertIn("DURATION", self.codes())

    def test_freshness_late(self):
        self.events[0]["ingested_at"] = "2026-09-05T07:00:00+00:00"
        self.assertIn("FRESHNESS", self.codes())

    def test_freshness_negative(self):
        self.events[0]["ingested_at"] = "2026-09-05T04:59:00+00:00"
        self.assertIn("FRESHNESS", self.codes())

    def test_quantity_invalid_values(self):
        for quantity in (-1, 0, 1.5, True, None, "12", self.order["planned_units"] + 1):
            with self.subTest(quantity=quantity):
                self.events[-1]["quantity"] = quantity
                self.assertIn("QUANTITY", self.codes())

    def test_units_not_assumed(self):
        self.events[-1]["unit"] = "kg"
        self.assertIn("UNIT", self.codes())

    def test_closed_missing_step(self):
        self.events.pop()
        self.assertIn("MISSING_STEP", self.codes())

    def test_open_incomplete_not_error(self):
        self.events = self.events[:2]
        self.order["state"] = "open"
        self.assertEqual(self.codes(), set())


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.path = Path(self.tmp.name) / "test.sqlite"
        self.db = initialize(self.path)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def act(self, action, actor="alex", iid="INC-1042", note="Checked BUF-1042 against source identity, count and timestamp."):
        v = self.db.execute("SELECT version FROM incidents WHERE id=?", (iid,)).fetchone()[0]
        return command(self.db, actor, action, dict(incident_id=iid, version=v, note=note))

    def recover(self):
        self.act("acknowledge")
        self.act("propose")
        self.act("approve", "sam")

    def test_schema_integrity(self):
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(rows(self.db, "PRAGMA foreign_key_check"), [])

    def test_idempotent_ingestion_and_refresh(self):
        before = snapshot(self.db)
        with self.db:
            self.assertEqual(ingest(self.db, generate()["events"]), 0)
            refresh(self.db)
        after = snapshot(self.db)
        self.assertEqual(before["metrics"], after["metrics"])
        self.assertEqual(before["findings"], after["findings"])
        self.assertEqual(before["source_rows"], after["source_rows"])

    def test_raw_collision_rolls_back_entire_batch(self):
        sample = payloads(self.db, "raw_events")[0]
        new = dict(sample, row_id="brand-new", event_id="new-event")
        changed = dict(sample, quantity=991)
        with self.assertRaisesRegex(ValueError, "Immutable"):
            command(self.db, "robin", "ingest", {"events": [new, changed]})
        self.assertIsNone(self.db.execute("SELECT 1 FROM raw_events WHERE row_id='brand-new'").fetchone())

    def test_raw_update_prohibited(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE raw_events SET hash='changed'")
        self.db.rollback()

    def test_malformed_batch_rejected(self):
        for events in ([], "not-array", [{"row_id":"x", "event_id":[]}], [{}], [{"row_id":[], "order_id":HERO,"kind":"complete"}]):
            with self.subTest(events=events), self.assertRaises(ValueError):
                command(self.db, "robin", "ingest", {"events": events})

    def test_orphan_source_kept_and_explained(self):
        event = dict(payloads(self.db,"raw_events")[0], row_id="orphan-row", event_id="orphan-event", order_id="MISSING")
        command(self.db, "robin", "ingest", {"events":[event]})
        s = snapshot(self.db)
        self.assertEqual(s["orphan_events"], [event])
        self.assertTrue(any(f["rule"] == "REFERENCE" and f["row_id"] == "orphan-row" for f in s["findings"]))
        self.assertNotIn("MISSING", s["all_order_ids"])

    def test_metric_reconciliation_to_raw_and_sql(self):
        s = snapshot(self.db)
        ids = {f["order_id"] for f in s["facts"] if f["trust"] == "trusted"}
        raw_total = sum(e["quantity"] for e in payloads(self.db, "raw_events") if e.get("order_id") in ids and e.get("kind") == "complete")
        self.assertEqual(raw_total, s["metrics"]["units"])
        self.assertEqual(raw_total, self.db.execute("SELECT SUM(units) FROM facts WHERE trust='trusted'").fetchone()[0])
        self.assertEqual(raw_total, sum(x["units"] for x in s["trend"]))
        self.assertEqual(raw_total, sum(x["units"] for x in s["station_metrics"]))
        self.assertEqual(s["metrics"]["held"], 6)
        self.assertEqual(s["metrics"]["incomplete"], 1)

    def test_filter_scope_reconciles(self):
        s = snapshot(self.db, {"from":"2026-11-15", "to":"2026-11-15", "station":"FILL-01", "shift":"Early"})
        self.assertEqual(s["metrics"]["orders"], 2)
        self.assertEqual(s["metrics"]["completed"], 1)
        self.assertEqual(s["metrics"]["held"], 1)
        self.assertEqual(sum(f["units"] or 0 for f in s["facts"]), s["metrics"]["units"])

    def test_exact_formulas_and_no_denominators(self):
        f = [dict(order_id="A",trust="trusted",state="closed",units=100,elapsed=60,late=0),
             dict(order_id="B",trust="trusted",state="closed",units=200,elapsed=120,late=1),
             dict(order_id="C",trust="held",state="closed",units=None,elapsed=None,late=None),
             dict(order_id="D",trust="incomplete",state="open",units=None,elapsed=None,late=None)]
        q = [dict(order_id="A",result="pass"),dict(order_id="B",result="fail"),dict(order_id="C",result="pass")]
        m = aggregate(f,q)
        self.assertEqual((m["units"],m["elapsed"],m["late_share"],m["check_rate"],m["coverage"]), (300,90,50,50,66.7))
        empty = aggregate([], [])
        self.assertIsNone(empty["elapsed"])
        self.assertIsNone(empty["late_share"])
        self.assertIsNone(empty["check_rate"])
        self.assertIsNone(empty["coverage"])

    def test_hero_preview_and_complete_human_journey(self):
        before = snapshot(self.db)["metrics"]
        original = rows(self.db, "SELECT * FROM raw_events")
        detail = order_detail(self.db, HERO)
        self.assertEqual(detail["preview"]["naive_elapsed"], 480)
        self.assertEqual(detail["preview"]["elapsed"], 190)
        self.assertFalse(detail["preview"]["applied"])
        self.recover()
        self.act("resolve", "sam")
        after = snapshot(self.db)["metrics"]
        detail = order_detail(self.db, HERO)
        self.assertEqual(after["units"] - before["units"], 720)
        self.assertEqual(after["completed"] - before["completed"], 1)
        self.assertEqual(after["held"], before["held"] - 1)
        self.assertEqual(detail["fact"]["elapsed"], 190)
        self.assertEqual(detail["fact"]["wait"], 140)
        self.assertEqual(detail["fact"]["late"], 1)
        self.assertEqual(detail["findings"], [])
        self.assertEqual({i["id"]:i["state"] for i in detail["incidents"]}, {"INC-1042":"resolved","INC-1043":"open"})
        self.assertEqual(len(detail["audit"]), 4)
        self.assertEqual(rows(self.db,"SELECT * FROM raw_events WHERE row_id != 'R-RECOVERY-1042'"), original)
        self.assertEqual([a["action"] for a in reversed(detail["audit"])], ["acknowledge","propose","approve","resolve"])
        self.assertEqual(json.loads(detail["audit"][1]["after_json"])["proposal"]["evidence_id"], "BUF-1042")

    def test_viewer_cannot_mutate_incident(self):
        with self.assertRaises(PermissionError):
            self.act("acknowledge", "jules")

    def test_operator_cannot_approve(self):
        self.act("acknowledge")
        self.act("propose")
        with self.assertRaises(PermissionError):
            self.act("approve", "alex")

    def test_self_approval_denied_even_for_supervisor(self):
        self.act("acknowledge", "sam")
        self.act("propose", "sam")
        with self.assertRaisesRegex(PermissionError, "own evidence"):
            self.act("approve", "sam")

    def test_admin_is_not_supervisor(self):
        self.act("acknowledge")
        self.act("propose")
        with self.assertRaises(PermissionError):
            self.act("approve", "robin")

    def test_only_admin_can_ingest_refresh_and_reset(self):
        for actor in ("alex", "sam", "jules", "unknown"):
            for action in ("refresh", "ingest"):
                with self.subTest(actor=actor,action=action), self.assertRaises(PermissionError):
                    command(self.db, actor, action, {"events":generate()["events"]})
            with self.assertRaises(PermissionError):
                reset(self.db, actor, "RESET")

    def test_illegal_transitions_and_unresolved_hold(self):
        with self.assertRaises(ValueError):
            self.act("propose")
        with self.assertRaises(ValueError):
            self.act("resolve", "sam")
        self.act("acknowledge")
        with self.assertRaisesRegex(ValueError, "Blocking"):
            self.act("resolve", "sam")
        with self.assertRaises(ValueError):
            self.act("acknowledge")

    def test_stale_revision_rejected(self):
        self.act("acknowledge")
        with self.assertRaisesRegex(ValueError, "changed"):
            command(self.db,"alex","note",dict(incident_id="INC-1042",version=0,note="Outdated view must not overwrite a review."))

    def test_short_note_rejected_without_audit(self):
        before = self.db.execute("SELECT count(*) FROM audit").fetchone()[0]
        with self.assertRaises(ValueError):
            self.act("acknowledge", note="yes")
        self.assertEqual(self.db.execute("SELECT count(*) FROM audit").fetchone()[0], before)

    def test_reject_then_repropose(self):
        self.act("acknowledge")
        self.act("propose")
        self.act("reject", "sam")
        self.assertEqual(order_detail(self.db,HERO)["fact"]["trust"], "held")
        self.act("propose")
        self.assertEqual(len(order_detail(self.db,HERO)["proposals"]), 2)

    def test_approval_rollback_if_other_findings_remain(self):
        self.act("acknowledge")
        self.act("propose")
        event = dict(order_detail(self.db,HERO)["events"][0], row_id="DUP-HERO")
        command(self.db,"robin","ingest",{"events":[event]})
        with self.assertRaisesRegex(ValueError, "still fails"):
            self.act("approve","sam")
        self.assertIsNone(self.db.execute("SELECT 1 FROM raw_events WHERE row_id='R-RECOVERY-1042'").fetchone())
        self.assertEqual(order_detail(self.db,HERO)["proposals"][0]["status"], "pending")

    def test_recovery_exactly_once_and_persistence(self):
        self.recover()
        with self.assertRaises(ValueError):
            self.act("approve","sam")
        self.db.close()
        self.db=initialize(self.path)
        self.assertEqual(order_detail(self.db,HERO)["fact"]["units"],720)
        self.assertEqual(len(order_detail(self.db,HERO)["events"]),4)

    def test_reopen_preserves_recovered_evidence(self):
        self.recover()
        self.act("resolve","sam")
        self.act("reopen","robin")
        detail=order_detail(self.db,HERO)
        self.assertEqual(detail["incidents"][0]["state"],"open")
        self.assertEqual(detail["fact"]["trust"],"trusted")

    def test_reset_deterministic_retains_audit_and_feedback(self):
        before=snapshot(self.db)["metrics"]
        self.recover()
        command(self.db,"jules","feedback",{"message":"Review steps are understandable."})
        reset(self.db,"robin","RESET")
        after=snapshot(self.db)
        self.assertEqual(after["metrics"],before)
        self.assertEqual(len(after["feedback"]),1)
        self.assertTrue(any(a["action"]=="approve" for a in after["audit"]))
        self.assertEqual(order_detail(self.db,HERO)["proposals"],[])

    def test_reset_requires_confirmation(self):
        with self.assertRaises(ValueError):
            reset(self.db,"robin","yes")

    def test_audit_update_prohibited(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE audit SET actor='other'")
        self.db.rollback()

    def test_method_confusion_matrices_reconcile(self):
        lab=snapshot(self.db)["lab"]
        self.assertEqual(lab["training"],432)
        self.assertEqual(lab["testing"],205)
        self.assertEqual(lab["positives"],6)
        self.assertEqual(lab["methods"][0]["recall"],.5)
        self.assertEqual(lab["methods"][1]["recall"],1.0)
        for m in lab["methods"]:
            self.assertEqual(m["tp"]+m["fp"]+m["fn"]+m["tn"],lab["testing"])
            self.assertEqual(m["tp"]+m["fn"],lab["positives"])

    def test_label_changes_do_not_change_scores(self):
        facts=rows(self.db,"SELECT * FROM facts")
        orders=payloads(self.db,"orders")
        before=method_lab(facts,orders)
        for order in orders:
            order["label"]=not order["label"]
        after=method_lab(facts,orders)
        self.assertEqual([s["score"] for s in before["signals"]],[s["score"] for s in after["signals"]])
        self.assertNotEqual(before["methods"],after["methods"])

    def test_test_period_does_not_change_baseline(self):
        facts=rows(self.db,"SELECT * FROM facts")
        orders=payloads(self.db,"orders")
        before=method_lab(facts,orders)
        for f in facts:
            if f["day"]>="2026-10-23" and f["trust"]=="trusted":
                f["wait"]+=1000
        self.assertEqual(before["baselines"],method_lab(facts,orders)["baselines"])

    def test_zero_mad_handled(self):
        facts=rows(self.db,"SELECT * FROM facts")
        for f in facts:
            if f["trust"]=="trusted":
                f["wait"]=20 if f["day"]<"2026-10-23" else 21
        lab=method_lab(facts,payloads(self.db,"orders"))
        self.assertTrue(all(s["score"]==999 for s in lab["signals"]))

    def test_absent_training_station_is_unavailable_not_a_crash(self):
        facts=rows(self.db,"SELECT * FROM facts")
        for f in facts:
            if f["day"] < "2026-10-23" and f["station"] == "FILL-01":
                f["trust"]="held"
        lab=method_lab(facts,payloads(self.db,"orders"))
        unavailable=[s for s in lab["signals"] if s["station"]=="FILL-01"]
        self.assertTrue(unavailable)
        self.assertTrue(all(s["score"] is None and s["robust"] is None for s in unavailable))
        self.assertEqual(lab["methods"][1]["unavailable"],len(unavailable))

    def test_invalid_date_filters_rejected(self):
        for filters in ({"from":"invalid"},{"from":"2026-11-16","to":"2026-11-15"},{"to":"20261115"}):
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                snapshot(self.db,filters)

    def test_new_invalid_evidence_reopens_resolved_data_incident(self):
        self.recover()
        self.act("resolve","sam")
        extra=dict(order_detail(self.db,HERO)["events"][0],row_id="RECURRENT-DUP")
        command(self.db,"robin","ingest",{"events":[extra]})
        detail=order_detail(self.db,HERO)
        self.assertEqual(detail["fact"]["trust"],"held")
        self.assertEqual(detail["incidents"][0]["state"],"open")
        self.assertEqual(detail["audit"][0]["action"],"validation_reopened")
        with self.db:
            refresh(self.db)
        self.assertEqual(len(order_detail(self.db,HERO)["audit"]),5)

    def test_zero_mad_shorter_wait_is_not_long_wait_signal(self):
        facts=rows(self.db,"SELECT * FROM facts")
        for f in facts:
            if f["trust"]=="trusted":
                f["wait"]=20 if f["day"]<"2026-10-23" else 19
        lab=method_lab(facts,payloads(self.db,"orders"))
        self.assertTrue(all(s["score"]==-999 and not s["robust"] for s in lab["signals"]))

    def test_admin_import_cannot_bypass_independent_hero_review(self):
        receipt=generate()["evidence"][0]["event"]
        with self.assertRaisesRegex(PermissionError,"independently reviewed"):
            command(self.db,"robin","ingest",{"events":[receipt]})
        self.assertEqual(order_detail(self.db,HERO)["fact"]["trust"],"held")
        self.recover()
        result=command(self.db,"robin","ingest",{"events":[receipt]})
        self.assertEqual(result["added"],0)

    def test_invalid_command_shapes_are_explained_without_writes(self):
        before=self.db.execute("SELECT count(*) FROM audit").fetchone()[0]
        with self.assertRaisesRegex(ValueError,"topic"):
            command(self.db,"jules","feedback",{"message":"Valid length message", "category":{}})
        with self.assertRaisesRegex(ValueError,"incident_id"):
            command(self.db,"alex","acknowledge",{"incident_id":[]})
        self.assertEqual(self.db.execute("SELECT count(*) FROM audit").fetchone()[0],before)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(dir=TEST_ROOT)
        cls.server=Server(("127.0.0.1",0),Path(cls.tmp.name)/"http.sqlite")
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def request(self,path,body=None,actor="alex",token=True,origin=True):
        headers={}
        if token: headers["X-CSRF-Token"]=self.server.csrf
        if origin: headers["Origin"]=self.base
        headers["X-Demo-Actor"]=actor
        req=Request(self.base+path, data=json.dumps(body).encode() if body is not None else None,headers=headers)
        try:
            with urlopen(req) as response:
                return response.status,response.read(),response.headers
        except HTTPError as error:
            return error.code,error.read(),error.headers

    def test_static_and_security_headers(self):
        for path in ('/','/app.js','/experience.js','/styles.css','/favicon.svg'):
            status,body,headers=self.request(path)
            self.assertEqual(status,200)
            self.assertTrue(body)
            self.assertIn("frame-ancestors 'none'",headers["Content-Security-Policy"])

    def test_path_traversal_not_served(self):
        self.assertEqual(self.request('/../shopflooriq/store.py')[0],404)

    def test_csrf_and_origin_enforced(self):
        for token,origin in ((False,True),(True,False)):
            self.assertEqual(self.request('/api/refresh',{},actor='robin',token=token,origin=origin)[0],403)

    def test_host_header_rejected(self):
        req=Request(self.base+'/api/state',headers={"Host":"external.invalid"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(req)
        self.assertEqual(caught.exception.code,403)

    def test_permissions_enforced_over_http(self):
        self.assertEqual(self.request('/api/refresh',{},actor='jules')[0],403)

    def test_filtered_export_reconciles(self):
        query='?from=2026-11-15&to=2026-11-15&station=PACK-02'
        state=json.loads(self.request('/api/state'+query)[1])
        status,body,headers=self.request('/api/export'+query)
        records=list(csv.DictReader(io.StringIO(body.decode())))
        self.assertEqual(status,200)
        self.assertEqual(sum(int(r['units']) for r in records),state['metrics']['units'])
        self.assertEqual(len(records),state['metrics']['completed'])
        self.assertIn('attachment',headers['Content-Disposition'])

    def test_unknown_order_returns_helpful_error(self):
        status,body,_=self.request('/api/order?id=NO-SUCH-ORDER')
        self.assertEqual(status,400)
        self.assertIn('not found',json.loads(body)['error'])

    def test_http_complete_journey(self):
        for action,actor in [('acknowledge','alex'),('propose','alex'),('approve','sam'),('resolve','sam')]:
            detail=json.loads(self.request('/api/order?id=WO-1042')[1])
            incident=next(i for i in detail['incidents'] if i['id']=='INC-1042')
            status,body,_=self.request('/api/'+action,dict(incident_id='INC-1042',version=incident['version'],note='HTTP acceptance: checked BUF-1042 identity, time and 720 units.'),actor=actor)
            self.assertEqual(status,200,body)
        detail=json.loads(self.request('/api/order?id=WO-1042')[1])
        self.assertEqual(detail['fact']['units'],720)
        self.assertEqual(detail['incidents'][0]['state'],'resolved')
        self.assertEqual(detail['incidents'][1]['state'],'open')

    def test_operational_http_plan_closure_and_reopen(self):
        def act(action,actor='sam',**extra):
            detail=json.loads(self.request('/api/order?id=WO-1042')[1])
            i=next(i for i in detail['incidents'] if i['id']=='INC-1043')
            body=dict(incident_id=i['id'],version=i['version'],note='HTTP review: observed fill and pack times; cause remains unknown.')
            body.update(extra)
            return self.request('/api/'+action,body,actor=actor)
        self.assertEqual(act('acknowledge')[0],200)
        plan=dict(next_action='Review the station log and compare material handoff timestamps before assigning a cause.',
                  missing_info='Station log and material availability evidence are not included in this synthetic dataset.',refs=['R-WO-1042-2'])
        self.assertEqual(act('plan',actor='jules',**plan)[0],403)
        self.assertEqual(act('plan',**plan)[0],200)
        state=json.loads(self.request('/api/state')[1])
        self.assertEqual(state['handover']['operational'][0]['plan']['next_action'],plan['next_action'])
        self.assertEqual(act('resolve')[0],400)
        fields=dict(confirm_resolution=True,outcome='administratively_closed',refs=['R-WO-1042-2'],
                    uncertainty='The cause is not established because station records remain unavailable for independent review.')
        self.assertEqual(act('resolve',actor='alex',**fields)[0],403)
        self.assertEqual(act('resolve',**fields)[0],200)
        self.assertEqual(act('reopen')[0],200)
        detail=json.loads(self.request('/api/order?id=WO-1042')[1])
        incident=next(i for i in detail['incidents'] if i['id']=='INC-1043')
        self.assertEqual(incident['state'],'open')
        self.assertEqual(incident['resolution']['cause_status'],'not_established')


if __name__=='__main__':
    unittest.main()
