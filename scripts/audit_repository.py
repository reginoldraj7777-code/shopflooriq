"""Audit indexed/history content and local Markdown links without uploading anything."""
import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_DIRS = {'data', 'backups', 'test-results', '.runtime', '.env', '.aws', '.codex',
                '.agents', '.venv', 'venv', 'node_modules', '__pycache__', '.vscode', '.idea'}
BLOCKED_FILES = {'shopflooriq_codex_master_brief.md', 'followup_notes.md',
                 'preservation_check.json', 'check_preservation.py', '.ds_store', 'thumbs.db'}
TEXT_EXTENSIONS = {'.py', '.js', '.cjs', '.json', '.md', '.html', '.css', '.svg',
                   '.txt', '.cmd', '.ps1', '.yml', '.yaml', '.toml', '.ini'}
SENSITIVE_PATTERNS = [
    ('private key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('GitHub token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b')),
    ('provider key', re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b')),
    ('AWS access key', re.compile(r'\bAKIA[A-Z0-9]{16}\b')),
    ('personal Windows path', re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+[^\s\\/"\']+', re.I)),
    ('personal Unix path', re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/')),
]


def git(root, *args):
    # Trust only the explicitly selected local checkout for this invocation.
    # This also supports Windows sandboxes whose file owner differs from Python's.
    result = subprocess.run(['git', '-c', 'safe.directory=' + str(Path(root).resolve()),
                             '-C', str(root), *args], capture_output=True)
    if result.returncode:
        # Git stderr may contain home paths or remote credentials; do not publish it.
        raise RuntimeError(f"git {' '.join(args[:2])} failed (exit {result.returncode}); check local repository access.")
    return result.stdout


def blocked_path(name):
    path = PurePosixPath(name.lower().replace('\\', '/'))
    return (any(part in BLOCKED_DIRS for part in path.parts)
            or path.name in BLOCKED_FILES
            or path.name == '.env' or path.name.startswith('.env.')
            or path.name.startswith('credentials')
            or '.sqlite' in path.name
            or bool(re.search(r'\.(?:db(?:-.*)?|log|pyc|pyo|pem|key|mp4|mov|mkv|webm)$', path.name)))


def content_issues(name, data):
    if Path(name).suffix.lower() not in TEXT_EXTENSIONS and Path(name).suffix:
        return []
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return [f'{name}: expected UTF-8 text']
    issues = []
    for label, pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(text):
            line = text.count('\n', 0, match.start()) + 1
            # Never echo matched credentials or private content into reports.
            issues.append(f'{name}:{line}: possible {label}')
    return issues


def link_issues(files):
    """Resolve relative Markdown links against the indexed package, case-sensitively."""
    issues = []
    checked = 0
    for name, data in files.items():
        if not name.endswith('.md'):
            continue
        text = data.decode('utf-8-sig')
        text = re.sub(r'```.*?```', '', text, flags=re.S)
        for match in re.finditer(r'!?\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', text):
            target = match.group(1).strip('<>')
            url = urlsplit(target)
            if url.scheme or url.netloc or target.startswith('#'):
                continue
            path = unquote(url.path)
            if not path:
                continue
            parts = list(PurePosixPath(name).parent.parts)
            for part in path.split('/'):
                if part == '..':
                    if not parts:
                        issues.append(f'{name}: link escapes repository: {target}')
                        break
                    parts.pop()
                elif part not in ('', '.'):
                    parts.append(part)
            else:
                resolved = '/'.join(parts)
                checked += 1
                if resolved not in files:
                    issues.append(f'{name}: target absent from index: {target}')
    return issues, checked


def audit(root=ROOT):
    names = [s for s in git(root, 'ls-files', '-z').decode().split('\0') if s]
    issues = [] if names else ['Git index is empty; stage the reviewed public files first.']
    files = {name: git(root, 'show', ':' + name) for name in names}
    for name, data in files.items():
        if blocked_path(name):
            issues.append(f'index: prohibited local file: {name}')
        issues.extend(content_issues(name, data))
    ignored = [s for s in git(root, 'ls-files', '-ci', '--exclude-standard', '-z').decode().split('\0') if s]
    issues.extend(f'index: ignored file is still tracked: {name}' for name in ignored)
    links, checked = link_issues(files)
    issues.extend(links)
    # Audit each reachable historical blob once; .gitignore cannot clean history.
    commits = git(root, 'rev-list', '--all').decode().splitlines()
    seen = set()
    for commit in commits:
        for entry in git(root, 'ls-tree', '-rz', commit).split(b'\0'):
            if not entry:
                continue
            metadata, encoded_name = entry.split(b'\t', 1)
            _, kind, oid = metadata.split()
            name = encoded_name.decode('utf-8')
            if blocked_path(name):
                issues.append(f'history {commit[:12]}: prohibited local file: {name}')
            if kind == b'blob' and (name, oid) not in seen:
                seen.add((name, oid))
                issues.extend(f'history {commit[:12]}: {issue}' for issue in content_issues(name, git(root, 'cat-file', 'blob', oid.decode())))
    report = dict(passed=not issues, indexed_files=len(files), relative_links_checked=checked,
                  commits_checked=len(commits), historical_blobs_checked=len(seen),
                  remotes_configured=len(git(root, 'remote').decode().splitlines()),
                  issues=sorted(set(issues)),
                  scope='Git index and all locally reachable commits; Markdown file targets, not external URLs or anchors.',
                  limits='Pattern scan is not proof that all secrets or personal information are absent. Review assets manually.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', help='Optional JSON report path; output is sanitized.')
    args = parser.parse_args()
    try:
        result = audit()
    except RuntimeError as error:
        result = dict(passed=False, issues=[str(error)])
    output = json.dumps(result, indent=2)
    if args.report:
        Path(args.report).write_text(output + '\n', encoding='utf-8')
    print(output)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
