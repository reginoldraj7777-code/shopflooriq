"""Fresh-database CLI startup smoke test; owns and terminates only its child server."""
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from queue import Queue, Empty
from time import perf_counter
from urllib.request import urlopen
from shopflooriq.store import ROOT

folder=ROOT/'test-results'
folder.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=folder) as tmp:
    path=Path(tmp)/'fresh.sqlite'
    start=perf_counter()
    process=subprocess.Popen([sys.executable,'-m','shopflooriq','serve','--db',str(path),'--port','0'],cwd=ROOT,
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    lines=Queue()
    reader=threading.Thread(target=lambda: lines.put(process.stdout.readline()),daemon=True)
    reader.start()
    try:
        line=lines.get(timeout=15)
        assert 'http://127.0.0.1:' in line,line
        url=line.strip().split(' | ')[-1]
        with urlopen(url,timeout=5) as response:
            assert response.status==200
            assert b'ShopfloorIQ' in response.read()
        ready_ms=round((perf_counter()-start)*1000,2)
        with urlopen(url+'/api/state',timeout=5) as response:
            state=json.load(response)
        assert state['source_rows']==2574
        assert state['metrics']['orders']==644
        assert len(state['findings'])==10
        report=dict(fresh_cli_start_to_http_ms=ready_ms,source_rows=state['source_rows'],orders=state['metrics']['orders'],findings=len(state['findings']),status='passed')
        (ROOT/'docs'/'cli_smoke_results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
    finally:
        process.terminate()
        process.wait(timeout=5)
        process.stdout.close()
        reader.join(timeout=2)
