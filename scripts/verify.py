"""Run all automated checks with durable results; all application writes are isolated."""
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
import unittest
from datetime import datetime, timezone
from shopflooriq.store import ROOT


def main():
    folder=ROOT/'test-results';folder.mkdir(exist_ok=True)
    results=dict(at=datetime.now(timezone.utc).isoformat(), platform=platform.system(), python=platform.python_version(), checks=[])
    # Verify every existing local SQLite file, including previous rehearsals.
    preserved={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
               for directory in ('data','backups') for p in (ROOT/directory).rglob('*.sqlite')}
    start=time.perf_counter()
    with (folder/'python-tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    results['checks'].append(dict(name='Python unittest',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),seconds=round(time.perf_counter()-start,3)))
    for name,args in [('UI fixtures',[sys.executable,'-m','scripts.make_ui_fixture']),
                      ('JavaScript tests',['node','--test','--test-reporter=tap','tests/ui.test.cjs']),
                      ('Controller syntax',['node','--check','web/app.js']),
                      ('Experience syntax',['node','--check','web/experience.js']),
                      ('CLI lifecycle',[sys.executable,'-m','scripts.verify_cli'])]:
        start=time.perf_counter()
        output=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        (folder/(name.lower().replace(' ','-')+'.txt')).write_text(output.stdout+output.stderr,encoding='utf-8')
        check=dict(name=name,command=['python' if a==sys.executable else a for a in args],passed=output.returncode==0,seconds=round(time.perf_counter()-start,3))
        if name=='JavaScript tests':
            for label,key in [('tests','tests'),('pass','passed_tests'),('fail','failures')]:
                match=re.search(r'^# '+label+r' (\d+)\s*$',output.stdout,re.M)
                if match:check[key]=int(match.group(1))
                else:check['passed']=False
        results['checks'].append(check)
    preservation=[dict(path=p,sha256=digest,unchanged=(ROOT/p).exists() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest) for p,digest in preserved.items()]
    # Local file names/fingerprints belong in ignored evidence, not public reports.
    (folder/'verification-preservation.json').write_text(json.dumps(preservation,indent=2),encoding='utf-8')
    results['existing_databases_unchanged']=all(p['unchanged'] for p in preservation)
    results['passed']=all(c['passed'] for c in results['checks']) and results['existing_databases_unchanged']
    (ROOT/'docs'/'verification_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
    return 0 if results['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
