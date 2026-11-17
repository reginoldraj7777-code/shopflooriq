"""Publication boundaries: index, history, privacy patterns and package links."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.audit_repository import ROOT, audit, blocked_path, content_issues, link_issues


class PublicationRules(unittest.TestCase):
    def test_nested_mutable_and_private_files_are_blocked(self):
        for path in ['data/new.json', 'x/run.sqlite-wal', 'backups/old.bin', 'x/.env.local',
                     'x/ShopfloorIQ_Codex_Master_Brief.md', 'test-results/log.txt', 'x/demo.mp4']:
            with self.subTest(path=path):
                self.assertTrue(blocked_path(path))

    def test_source_and_real_visual_paths_are_allowed(self):
        for path in ['shopflooriq/store.py', 'assets/mission-control.png', '.github/workflows/ci.yml']:
            self.assertFalse(blocked_path(path))

    def test_secret_detection_redacts_actual_value(self):
        secret = 'ghp_' + 'a' * 36
        findings = content_issues('example.md', ('text\n' + secret).encode())
        self.assertEqual(findings, ['example.md:2: possible GitHub token'])
        self.assertNotIn(secret, str(findings))

    def test_personal_paths_are_detected(self):
        path = 'C:' + '\\Users\\' + 'ExamplePerson\\project'
        self.assertTrue(content_issues('example.json', path.encode()))

    def test_links_resolve_parent_and_encoded_spaces(self):
        files = {'docs/a.md': b'[image](../assets/diagram%20one.svg)', 'assets/diagram one.svg': b'<svg/>'}
        self.assertEqual(link_issues(files), ([], 1))

    def test_links_reject_missing_or_wrong_case_index_target(self):
        files = {'README.md': b'[x](docs/a.md) ![y](assets/Hero.png)', 'assets/hero.png': b'png'}
        issues, count = link_issues(files)
        self.assertEqual(count, 2)
        self.assertEqual(len(issues), 2)

    def test_external_links_and_code_examples_not_treated_as_files(self):
        files = {'README.md': b'[x](https://example.invalid)\n```md\n[x](missing.md)\n```'}
        self.assertEqual(link_issues(files), ([], 0))


class GitPublicationAudit(unittest.TestCase):
    def setUp(self):
        folder = ROOT / 'test-results'
        folder.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=folder)
        self.root = Path(self.temp.name)
        self.run_git('init', '-b', 'main')

    def tearDown(self):
        self.temp.cleanup()

    def run_git(self, *args):
        subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def test_empty_index_fails(self):
        self.assertFalse(audit(self.root)['passed'])

    def test_audit_reads_staged_content_not_working_replacement(self):
        self.write('README.md', 'ghp_' + 'b' * 36)
        self.run_git('add', 'README.md')
        self.write('README.md', 'Safe working copy, unsafe index.')
        self.assertFalse(audit(self.root)['passed'])

    def test_ignored_private_files_do_not_enter_package(self):
        self.write('.gitignore', 'data/\n')
        self.write('data/example.sqlite', 'local only')
        self.write('README.md', 'Synthetic demo')
        self.run_git('add', '.gitignore', 'README.md')
        result = audit(self.root)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['indexed_files'], 2)

    def test_removing_file_from_index_does_not_hide_unsafe_history(self):
        self.write('data/example.sqlite', 'synthetic private fixture')
        self.write('README.md', 'Synthetic demo')
        self.run_git('add', 'data/example.sqlite', 'README.md')
        self.run_git('-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid',
                     '-c', 'commit.gpgsign=false', 'commit', '-m', 'Test fixture only')
        self.run_git('rm', '--cached', 'data/example.sqlite')
        result = audit(self.root)
        self.assertFalse(result['passed'])
        self.assertTrue(any(issue.startswith('history ') for issue in result['issues']))


if __name__ == '__main__':
    unittest.main()
