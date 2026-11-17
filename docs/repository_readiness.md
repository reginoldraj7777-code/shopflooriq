# Local publication review

Recommended repository name: **`shopflooriq`**

Recommended description:

> Synthetic manufacturing intelligence with traceable KPIs, data-quality checks, independently reviewed evidence recovery and explainable anomaly evaluation.

Suggested topics: `manufacturing`, `manufacturing-analytics`, `data-quality`, `data-provenance`, `industrial-analytics`, `anomaly-detection`, `human-in-the-loop`, `python`, `sqlite`, `javascript`, `synthetic-data`, `portfolio-project`.

## Prepared locally

- A focused [README](../README.md) with authentic application captures, a labeled editorial KPI comparison, source-grounded architecture visual, reproducible hero walkthrough and explicit before/after denominators.
- [Architecture](architecture.md), [data dictionary](data_dictionary.md), [metric contract](metric_definitions.md), [quality rules](quality_and_governance.md), [method evaluation](ai_methods_evaluation.md) and [limitations](limitations.md).
- MIT license as the local default, contribution guidance, security boundaries and consistent text-file conventions. No third-party runtime libraries, fonts or logo packages are bundled.
- An isolated recording launcher, sanitized verification reports, an indexed-content/history audit and a clean-export test runner.
- A [CI matrix](../.github/workflows/ci.yml) for Windows/Ubuntu and Python 3.11/3.12 with Node 24. Official Actions are pinned to full commit IDs; no secrets or deployment steps are used. Hosted results remain unverified.

## Publication safety

The folder had no Git repository, tracked files, commits or remote before this pass. A local `main` repository was initialized and only reviewed public files were staged. No commit, remote, push, visibility change or company contact was performed.

The private master brief remains on disk. `.gitignore` excludes it, all runtime data and recording databases, backups, test outputs, environment files, keys, caches, local configuration and unapproved videos. Private follow-up notes and local preservation reports are also excluded. Existing databases and backups were retained unchanged.

The [publication audit](publication_audit.json) inspects **the actual Git index**, ignored-but-tracked files and every locally reachable commit. It scans text for selected credential/private-path patterns without printing matching values and resolves relative Markdown file targets against indexed files, including case. It does not validate external URLs, heading anchors, unreachable Git objects or every possible secret format. Manual content review remains necessary.

Run after staging future edits:

```sh
python -m scripts.audit_repository
python -m scripts.verify_clean_export
```

An ignored file may still be in an old commit. If the audit detects this, remove sensitive content from the intended publication history before pushing; `.gitignore` alone is insufficient. No unsafe prior history was present in this newly initialized repository.

## Four-perspective review

| Perspective | Question | Result and correction |
|---|---|---|
| Hiring manager, 60 seconds | What problem does this solve, and what is distinctive? | README opens with the actual dashboard, then follows the reporting gap versus real wait through two actors, a measured KPI comparison and an evidence-linked handover. Architecture follows the product showcase. |
| Senior analytics engineer | Are the numbers and conclusions defensible? | Cohort/denominator contract, raw-to-fact reconciliation, small-positive-sample caveat and weak stress results are linked. Reporting recovery is never described as productivity gain. |
| Developer on a fresh checkout | Can I run it without local artifacts? | No runtime packages; fresh-session command; isolated full-suite export; exact locally verified environment. Other OS claims are explicitly deferred to CI. |
| Synthetic-data/security reviewer | Could this leak private context or imply real factory access? | Private material is excluded from the index; reports no longer contain interpreter home paths. Demo identities, mutable SQLite audit and loopback-only scope are explicit. No company branding or affiliation claim is introduced. |

This is a structured self-review, not an external security audit or independent endorsement.

## Files prepared in this pass

| Change | Files |
|---|---|
| New public repository setup | `.editorconfig`, `.gitattributes`, `.github/workflows/ci.yml`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md` |
| New visual/documentation assets | `assets/architecture.svg`, `assets/README.md`, `docs/repository_readiness.md` |
| New verification tooling/evidence | `scripts/audit_repository.py`, `scripts/verify_clean_export.py`, `tests/test_repository.py`, `docs/publication_audit.json`, `docs/clean_export_results.json` |
| Revised entry points | `README.md`, `ACCEPTANCE.md`, `.gitignore`, `scripts/verify.py` |
| Revised existing guides | `docs/architecture.md`, `docs/ai_methods_evaluation.md`, `docs/innovation_decisions.md`, `docs/limitations.md`, `docs/operator_quickstart.md`, `docs/quality_and_governance.md`, `demo/hero_scenario.md`, `demo/video_script.md` |
| Refreshed measured reports | `docs/verification_results.json`, `docs/measured_results.json`, `docs/cli_smoke_results.json` |
| Formatting only | Removed a trailing blank line in `tests/test_improvements.py`; no test logic changed |

Application source, schema, original data, existing launchers and private planning content were not changed. Prior README/acceptance versions and detailed preservation evidence remain in ignored local files. A fresh synthetic capture session and a clean test export were created separately during the initial repository pass. That pass staged 56 public files without application screenshots.

## Visual integration — 17 November 2026

Read `README_VISUAL_INSERT.md` and the supplied [application instructions](HOW_TO_APPLY.md), then inspected all eight PNGs in `assets/portfolio/`: seven authentic application captures and one editorial comparison. The README now leads with Mission Control, links each review step to its actual capture, shows the reporting comparison and handover, and places the architecture below the product showcase. Installation commands, engineering decisions, test instructions and substantive limitations are retained.

The [visual gallery](../assets/README.md), [provenance](ASSET_PROVENANCE.md), [acceptance record](../ACCEPTANCE.md) and [limitations](limitations.md) distinguish observed screenshot states from unverified live interaction. No images were edited, no application code or data was changed, and no video was introduced. The current indexed-file and link counts are recorded in the [publication audit](publication_audit.json).

## Remaining gates

1. Complete the [browser acceptance checklist](../ACCEPTANCE.md), including keyboard, layout and file-dialog behavior, then rehearse the recording. Supplied screenshots are now present and reviewed.
2. After a separately authorized publication, observe the first hosted CI runs and GitHub Markdown/SVG rendering. There is deliberately no passing CI badge yet.

The README, authentic visual package and technical evidence are ready for local portfolio review. Final screen recording remains conditional on live browser checks and rehearsal. Nothing has been published.
