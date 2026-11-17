# Developing ShopfloorIQ

Keep the demonstration synthetic, local and reproducible. No factory records, personal correspondence, credentials or real operational claims belong in this repository.

## Set up

Install Python 3.11+, Git and Node.js 24; no pip or npm package installation is required. Windows/Python 3.12.0/Node 24.19.0 is the locally verified environment. Ubuntu and Python 3.11 are configured CI targets, not yet observed hosted results. Run commands from the repository root.

```sh
python -m scripts.recording
```

The printed path identifies a new, isolated database. Use this for experimentation. Never reset or overwrite an existing database to make a test pass. The legacy reset command is only for deliberately disposable test fixtures.

## Verify changes

```sh
python -m scripts.verify
python -m scripts.benchmark
python -m scripts.audit_repository
```

`verify` runs Python discovery, generates disposable fixtures, runs Node UI tests, checks JavaScript syntax and starts a real child HTTP server on an assigned loopback port. Reports in `docs/` contain sanitized results; detailed output stays under ignored `test-results/`. Application writes are isolated. The runner fingerprints existing SQLite sessions before and after the checks.

For targeted work:

```sh
python -m unittest discover -s tests -v
python -m scripts.make_ui_fixture
node --test tests/ui.test.cjs
```

The Node suite tests renderers and handlers using a VM, not an actual browser DOM. Use the [manual acceptance checklist](ACCEPTANCE.md) for focus, layout and file dialogs.

## Review changes

Keep analytical definitions in sync with the [metric dictionary](docs/metric_definitions.md). Recovery changes must preserve atomicity, independent approval, source references and the separate operational incident. New detector results need actual confusion counts, abstentions and held-out methodology—not just an attractive score.

Stage only reviewed public files. Run the publication audit **after staging** because it reads the index, not unstaged edits. It also scans all locally reachable Git history; removing a secret from the current tree is insufficient. Never force-add ignored databases, the private planning brief, raw logs or recordings.

To rehearse a clean package from the staged index:

```sh
python -m scripts.verify_clean_export
```

This creates a new ignored export, runs the suite there, and leaves it available for inspection. It neither commits nor pushes. Read [security boundaries](SECURITY.md) and the [publication review](docs/repository_readiness.md) before sharing.
