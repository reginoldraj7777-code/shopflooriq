"""Build disposable, current data for the JavaScript rendering tests."""
import json
import tempfile
from pathlib import Path
from shopflooriq.store import ROOT, initialize, command
from shopflooriq.analytics import snapshot, order_detail

folder = ROOT / "test-results"
folder.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=folder) as tmp:
    db = initialize(Path(tmp) / "fixture.sqlite")
    seed = snapshot(db, {"from":"2026-11-02","to":"2026-11-15"})
    seed["csrf"] = "test-token"
    fixture = dict(seed=seed, hero=order_detail(db,"WO-1042"), other=order_detail(db,"WO-2631"),
                   duplicate=order_detail(db,"WO-2630"), open=order_detail(db,"WO-OPEN-01"))
    for action,actor in [('acknowledge','alex'),('propose','alex'),('approve','sam'),('resolve','sam')]:
        version=db.execute("SELECT version FROM incidents WHERE id='INC-1042'").fetchone()[0]
        command(db,actor,action,dict(incident_id='INC-1042',version=version,note='Verified BUF-1042 against order, timestamp and count.'))
        fixture[action]=order_detail(db,"WO-1042")
    fixture["resolved_state"]=snapshot(db,{"from":"2026-11-02","to":"2026-11-15"})
    command(db,'sam','acknowledge',dict(incident_id='INC-1043',version=0,note='Reviewed fill and pack timestamps; the cause remains undetermined.'))
    command(db,'sam','plan',dict(incident_id='INC-1043',version=1,
        note='Review the station log and compare the material handoff timestamps.',
        next_action='Review the station log and compare the material handoff timestamps.',
        missing_info='Station log entries and material availability records are not present in this dataset.',
        refs=['R-WO-1042-2','R-WO-1042-3']))
    fixture['operational']=order_detail(db,'WO-1042')
    fixture['handover_state']=snapshot(db,{'from':'2026-11-02','to':'2026-11-15'})
    (folder/"ui-fixture.json").write_text(json.dumps(fixture),encoding="utf-8")
    db.close()
print("Wrote isolated UI fixtures")
