"""Measure a clean seed, query, recovery, and SQLite footprint on this machine."""
import json
import platform
import tempfile
from pathlib import Path
from time import perf_counter
from shopflooriq.store import ROOT, initialize, command
from shopflooriq.analytics import snapshot, order_detail

folder=ROOT/"test-results"
folder.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=folder) as tmp:
    path=Path(tmp)/"measure.sqlite"
    start=perf_counter()
    db=initialize(path)
    seed_ms=(perf_counter()-start)*1000
    start=perf_counter()
    full=snapshot(db)
    query_ms=(perf_counter()-start)*1000
    selected=snapshot(db,{"from":"2026-11-02","to":"2026-11-15"})
    before=selected["metrics"]
    for action,actor in [('acknowledge','alex'),('propose','alex'),('approve','sam'),('resolve','sam')]:
        revision=db.execute("SELECT version FROM incidents WHERE id='INC-1042'").fetchone()[0]
        command(db,actor,action,dict(incident_id='INC-1042',version=revision,note='Acceptance measurement: verified BUF-1042 order, count and completion.'))
    after=snapshot(db,{"from":"2026-11-02","to":"2026-11-15"})["metrics"]
    report=dict(python=platform.python_version(),platform=platform.system(),seed=1042,
                initialization_ms=round(seed_ms,2),full_snapshot_ms=round(query_ms,2),database_bytes=path.stat().st_size,
                initial_source_rows=full['source_rows'],initial_findings=len(full['findings']),
                all_days_before=full['metrics'],last_14_days_before=before,last_14_days_after=after,
                evaluation={k:v for k,v in full['lab'].items() if k!='signals'},
                hero_after=order_detail(db,'WO-1042')['fact'])
    db.close()
(ROOT/'docs'/'measured_results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
