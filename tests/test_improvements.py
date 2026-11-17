"""Regression tests for the improvement pass; never write to the user's database."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from shopflooriq.store import initialize, command, rows, ROOT, payloads
from shopflooriq.analytics import snapshot, order_detail
from shopflooriq.investigation import context
from shopflooriq.methods import stress_data, stress_evaluation, fit, score, metrics
from shopflooriq.server import reset


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'test-results')
        self.path = Path(self.temp.name)/'isolated.sqlite'
        self.db = initialize(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def act(self, action, actor='sam', iid='INC-1043', **extra):
        version=self.db.execute('SELECT version FROM incidents WHERE id=?',(iid,)).fetchone()[0]
        body=dict(incident_id=iid,version=version,note='Reviewed the source event times and recorded the remaining investigation question.')
        body.update(extra)
        return command(self.db,actor,action,body)

    def closure(self):
        return dict(confirm_resolution=True,outcome='administratively_closed',refs=['R-WO-1042-2'],
                    uncertainty='The station records are unavailable and the underlying cause remains undetermined.')

    def plan(self):
        return dict(next_action='Review the station log and compare material handoff timestamps with packing start.',
                    missing_info='Station log entries and material availability records are not present in this dataset.',refs=['R-WO-1042-2','R-WO-1042-3'])

    def test_operational_closure_requires_explicit_complete_decision(self):
        self.act('acknowledge')
        for missing in ['confirm_resolution','outcome','uncertainty','refs']:
            fields=self.closure();fields.pop(missing)
            with self.subTest(missing=missing),self.assertRaises(ValueError):self.act('resolve',**fields)
        self.assertEqual(len(rows(self.db,'SELECT * FROM audit')),2)
        self.assertEqual(rows(self.db,"SELECT state FROM incidents WHERE id='INC-1043'")[0]['state'],'acknowledged')

    def test_short_or_repetitive_resolution_rejected(self):
        self.act('acknowledge')
        for note in ['done now thanks','closed '*15]:
            with self.subTest(note=note),self.assertRaises(ValueError):self.act('resolve',note=note,**self.closure())

    def test_closure_permissions_and_root_cause_claim_rejected(self):
        self.act('acknowledge')
        for actor in ['alex','robin','jules']:
            with self.subTest(actor=actor),self.assertRaises(PermissionError):self.act('resolve',actor=actor,**self.closure())
        with self.assertRaises(ValueError):self.act('resolve',**dict(self.closure(),outcome='root_cause_confirmed'))

    def test_mitigation_needs_recorded_verification(self):
        self.act('acknowledge')
        fields=dict(self.closure(),outcome='mitigated')
        with self.assertRaises(ValueError):self.act('resolve',**fields)
        result=self.act('resolve',**fields,action_taken='A simulated follow-up check found the queue cleared; longer-term verification remains outstanding.')
        self.assertEqual(result['resolution']['cause_status'],'not_established')

    def test_closure_audit_persistence_and_reopening_preserve_evidence(self):
        self.act('acknowledge');self.act('resolve',**self.closure())
        raw=payloads(self.db,'raw_events'); audits=rows(self.db,'SELECT * FROM audit')
        self.db.close();self.db=initialize(self.path)
        self.assertEqual(context(self.db,'INC-1043')['resolution']['outcome'],'administratively_closed')
        self.act('reopen')
        self.assertEqual(raw,payloads(self.db,'raw_events'))
        self.assertEqual(audits,rows(self.db,'SELECT * FROM audit')[:len(audits)])
        self.assertEqual(context(self.db,'INC-1043')['resolution']['cause_status'],'not_established')
        self.assertEqual(order_detail(self.db,'WO-1042')['incidents'][1]['state'],'open')

    def test_wrong_order_or_fabricated_reference_rejected(self):
        self.act('acknowledge')
        for refs in [[],['made-up'],['R-WO-2630-1'],'R-WO-1042-2',[{}]]:
            with self.subTest(refs=refs),self.assertRaises(ValueError):self.act('plan',**dict(self.plan(),refs=refs))

    def test_plan_permissions_and_lifecycle(self):
        with self.assertRaises(ValueError):self.act('plan',**self.plan())
        self.act('acknowledge')
        with self.assertRaises(PermissionError):self.act('plan',actor='jules',**self.plan())
        self.act('plan',**self.plan());self.act('resolve',**self.closure())
        with self.assertRaises(ValueError):self.act('plan',**self.plan())

    def test_recorded_next_step_survives_notes_refresh_and_restart(self):
        self.act('acknowledge');self.act('plan',**self.plan());self.act('note')
        command(self.db,'robin','refresh',{})
        self.db.close();self.db=initialize(self.path)
        item=snapshot(self.db)['handover']['operational'][0]
        self.assertEqual(item['plan']['next_action'],self.plan()['next_action'])
        self.assertEqual(item['owner'],'sam')
        self.assertEqual(item['plan']['actor'],'sam')
        self.assertEqual(item['plan']['audit_id'],3)

    def test_stale_plan_does_not_overwrite(self):
        self.act('acknowledge');self.act('plan',**self.plan())
        with self.assertRaisesRegex(ValueError,'changed'):
            command(self.db,'sam','plan',dict(incident_id='INC-1043',version=1,note='Outdated plan must not replace the current investigation.',**self.plan()))

    def test_complete_handover_includes_operational_and_every_hold(self):
        s=snapshot(self.db);h=s['handover']
        self.assertEqual(h['operational'][0]['id'],'INC-1043')
        self.assertEqual(h['open_count'],7)
        self.assertEqual(len(h['data']),6)
        self.assertEqual({r['order_id'] for r in h['held']},{f['order_id'] for f in s['facts'] if f['trust']=='held'})
        self.assertIn('not actual loss',h['ranking'])

    def test_handover_filter_empty_scope_and_outside_count(self):
        h=snapshot(self.db,dict(station='PACK-03',shift='Night',**{'from':'2026-11-16','to':'2026-11-17'}))['handover']
        self.assertEqual(h['open_count'],0);self.assertEqual(h['outside_scope'],7)
        self.assertEqual(h['held'],[]);self.assertEqual(h['scope']['station'],'PACK-03')

    def test_handover_has_no_silent_long_list_limit(self):
        with self.db:
            for j in range(30):self.db.execute("INSERT INTO incidents(id,order_id,title,category) VALUES(?,?,?,?)",(f'EXTRA-{j}','WO-1042','Synthetic test-only investigation','operational'))
        h=snapshot(self.db)['handover'];self.assertEqual(len(h['operational']),31);self.assertEqual(h['open_count'],37)

    def test_reset_does_not_resurrect_historical_plan(self):
        self.act('acknowledge');self.act('plan',**self.plan())
        reset(self.db,'robin','RESET')
        self.assertIsNone(context(self.db,'INC-1043')['plan'])
        self.assertTrue(any(a['action']=='plan' for a in rows(self.db,'SELECT * FROM audit')))

    def test_duplicate_order_never_shows_validated_steps(self):
        d=order_detail(self.db,'WO-2630')
        self.assertTrue(all(s['status']=='Evidence held' for s in d['steps']))
        self.assertEqual(len(d['steps'][-1]['events']),2)
        self.assertIn('DUPLICATE',{f['rule'] for f in d['steps'][-1]['findings']})

    def test_recovery_status_and_handover_reconcile_without_closing_operational(self):
        before=snapshot(self.db,{'from':'2026-11-02','to':'2026-11-15'})
        for action,actor in [('acknowledge','alex'),('propose','alex'),('approve','sam'),('resolve','sam')]:self.act(action,actor,iid='INC-1042')
        after=snapshot(self.db,{'from':'2026-11-02','to':'2026-11-15'})
        self.assertEqual(after['metrics']['units']-before['metrics']['units'],720)
        self.assertEqual(after['metrics']['completed'],116)
        self.assertNotIn('INC-1042',[i['id'] for i in after['handover']['data']])
        self.assertEqual(after['handover']['operational'][0]['id'],'INC-1043')
        d=order_detail(self.db,'WO-1042')
        self.assertEqual(d['steps'][-1]['status'],'Recovered · approved')
        self.assertTrue(d['preview']['applied']);self.assertEqual(len(after['trust_impact']),5)

    def test_global_trust_metrics_and_priority_do_not_follow_dashboard_filter(self):
        a=snapshot(self.db);b=snapshot(self.db,{'station':'FILL-01'})
        self.assertEqual(a['global_metrics'],b['global_metrics']);self.assertEqual(a['trust_impact'],b['trust_impact'])
        h=a['trust_impact'];self.assertEqual(h,sorted(h,key=lambda x:(-x['planned_units'],x['order_id'])))
        self.assertEqual(a['global_metrics']['orders'],a['global_metrics']['completed']+len(h)+a['global_metrics']['incomplete'])

    def test_new_hold_preserves_approval_history_but_excludes_recovered_order(self):
        for action,actor in [('acknowledge','alex'),('propose','alex'),('approve','sam')]:self.act(action,actor,iid='INC-1042')
        event=dict(order_detail(self.db,'WO-1042')['events'][0],row_id='NEW-DUPLICATE')
        command(self.db,'robin','ingest',{'events':[event]})
        detail=order_detail(self.db,'WO-1042');s=snapshot(self.db)
        self.assertTrue(detail['preview']['applied']);self.assertEqual(detail['preview']['current_trust'],'held')
        self.assertTrue(s['featured_recovery_approved']);self.assertEqual(s['featured_fact']['trust'],'held')
        self.assertIsNone(detail['fact']['units'])

    def test_held_open_order_does_not_inflate_closed_coverage_denominator(self):
        event=dict(order_detail(self.db,'WO-OPEN-01')['events'][0],row_id='DUP-OPEN')
        command(self.db,'robin','ingest',{'events':[event]})
        m=snapshot(self.db)['global_metrics']
        self.assertEqual(m['held'],7);self.assertEqual(m['closed'],643)
        self.assertEqual(m['coverage'],round(100*m['completed']/643,1))


class StressTests(unittest.TestCase):
    def test_protocol_determinism_and_full_matrix_reconciliation(self):
        s=stress_evaluation();self.assertEqual(s['total_testing'],6000)
        for c in s['conditions']:
            for m in [c['fixed'],*c['thresholds']]:
                self.assertEqual(m['tp']+m['fp']+m['fn']+m['tn']+m['unavailable'],c['testing'])
        stress_evaluation.cache_clear();self.assertEqual(s,stress_evaluation())

    def test_additional_conditions_expose_false_alerts_and_misses(self):
        s=stress_evaluation()
        self.assertGreater(sum(c['thresholds'][1]['fp'] for c in s['conditions']),0)
        self.assertGreater(sum(c['thresholds'][1]['fn'] for c in s['conditions']),0)
        self.assertEqual({x['outcome'] for x in s['examples']},{'false_positive','false_negative'})

    def test_low_sample_abstention_is_not_perfect_accuracy(self):
        c=next(c for c in stress_evaluation()['conditions'] if c['key']=='small')
        for m in c['thresholds']:
            self.assertEqual(m['unavailable'],1000);self.assertEqual(m['evaluated'],0)
            self.assertIsNone(m['precision']);self.assertIsNone(m['recall'])

    def test_zero_mad_and_missing_baselines(self):
        b=fit([30]*25)
        self.assertEqual([score(v,b) for v in [29,30,31]],[-999,0,999])
        self.assertIsNone(score(100,fit([30]*19)));self.assertIsNone(score(100,None))

    def test_class_imbalance_and_threshold_sensitivity(self):
        c=next(c for c in stress_evaluation()['conditions'] if c['key']=='rare')
        self.assertEqual(c['fixed']['positives'],10);self.assertEqual(c['fixed']['prevalence'],.01)
        for c in stress_evaluation()['conditions']:
            alerts=[m['tp']+m['fp'] for m in c['thresholds']]
            self.assertEqual(alerts,sorted(alerts,reverse=True))

    def test_future_observations_and_labels_cannot_change_fit_or_scores(self):
        train,test,labels=stress_data(11,'overlap');baseline=fit(train)
        scores=[score(v,baseline) for v in test]
        changed=[not y for y in labels]
        self.assertNotEqual(metrics([s>3.5 for s in scores],labels),metrics([s>3.5 for s in scores],changed))
        self.assertEqual(scores,[score(v,fit(train)) for v in test])
        test[:]=[v+1000 for v in test];self.assertEqual(baseline,fit(train))
