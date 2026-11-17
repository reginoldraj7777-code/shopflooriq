"""Export only the audited Git index and run the full suite in a new local folder."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.audit_repository import ROOT, audit, git


def main():
    publication = audit()
    if not publication['passed']:
        print(json.dumps(publication, indent=2))
        return 1
    folder = ROOT / 'test-results'
    folder.mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix='clean-export-', dir=folder))
    digest = hashlib.sha256()
    names = sorted(s for s in git(ROOT, 'ls-files', '-z').decode().split('\0') if s)
    for name in names:
        payload = git(ROOT, 'show', ':' + name)
        digest.update(name.encode() + b'\0' + payload + b'\0')
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    # No .git, runtime data, private brief or original database is copied.
    assert not any((destination / name).exists() for name in ('data', 'backups', '.git', 'ShopfloorIQ_Codex_Master_Brief.md'))
    run = subprocess.run([sys.executable, '-m', 'scripts.verify'], cwd=destination,
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    (destination / 'clean-export-run.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
    report_path = destination / 'docs' / 'verification_results.json'
    verification = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else None
    report = dict(passed=run.returncode == 0 and bool(verification and verification['passed']),
                  source='Reviewed Git index; no private local state copied',
                  indexed_files=len(names), index_content_sha256=digest.hexdigest(),
                  platform=verification.get('platform') if verification else None,
                  python=verification.get('python') if verification else None,
                  checks=verification.get('checks', []) if verification else [])
    (ROOT / 'docs' / 'clean_export_results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Local export retained:', destination.relative_to(ROOT).as_posix())
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
