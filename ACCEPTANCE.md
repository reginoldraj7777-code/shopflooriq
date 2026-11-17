# Verification and acceptance

Last local verification: **16 November 2026 · Windows · Python 3.12.0 · Node 24.19.0**.

The automated application workflow passes. Seven supplied application screenshots and one editorial comparison were inspected and integrated on **17 November 2026**. Live browser acceptance and final recording sign-off remain outstanding. No hosted CI result or production deployment is claimed.

## Executed checks

| Check | Result | Scope |
|---|---|---|
| Python unittest discovery | **102 passed** | 91 domain/HTTP tests plus 11 repository-publication tests |
| JavaScript `node:test` | **42 passed** | Actual renderers and handlers executed in a Node VM |
| Both JavaScript syntax checks | Passed | `web/app.js` and `web/experience.js` |
| Fresh CLI / HTTP startup | Passed | New temporary SQLite; 644 orders, 2,574 raw rows, 10 findings |
| Windows recording launcher | Passed | Clean export; HTTP 200; default cohort 86,880 units / 115 completed / 6 held |
| Clean indexed export | See [run evidence](docs/clean_export_results.json) | Full suite run without copied databases, caches or private files |
| KPI and detector measurements | See [measured results](docs/measured_results.json) | Isolated seed and independently approved recovery |
| Git publication audit | See [audit results](docs/publication_audit.json) | Indexed content, locally reachable history and relative Markdown targets |

**144 automated tests total.** Run `python -m scripts.verify` to reproduce the test suite. Exact durations, commands and counts are in [verification_results.json](docs/verification_results.json); detailed logs stay in ignored `test-results/`. Git and Node.js 24 are required for developer tests. No pip/npm installation is needed.

The baseline 133 application tests were rerun before repository work. The additional 11 tests check ignored/private paths, credential redaction, personal-path detection, package links, indexed content versus working files, and unsafe history even after removal from the index.

## Visual-package checks — 17 November 2026

This documentation-only integration reran the **11 publication regression tests: all passed**. The 144-test full-suite result above remains the recorded 16 November run; the application suite was not rerun for these documentation and asset changes.

| Check | Result |
|---|---|
| Supplied PNGs | All 8 visually inspected and fully decoded; 7 application captures plus 1 labeled editorial comparison; no PNG metadata reported |
| Existing SVGs | Architecture and favicon XML validated |
| Relative targets | All 88 indexed Markdown file/image links and all 3 heading links resolved, with exact filename case |
| Publication safety | 67 indexed public files; zero findings; no ignored files tracked, project commits or remotes |
| Preservation | All 21 protected application/data/brief files matched their starting hashes; installation section, engineering table/explanation and shell examples preserved |

The image files were not edited. File decoding and link resolution do not claim a hosted GitHub render or live browser acceptance.

## What the tests establish

Real HTTP tests execute the hero acknowledge → propose → independent approve → resolve journey and the operational acknowledge → plan → rejected incomplete closure → documented closure → reopen journey. They check role restrictions, stale revisions, self-approval rejection, transaction rollback, source/audit update guards, persistence, malformed imports, idempotence and reconciliation from raw evidence to SQL facts and API metrics.

Regression checks cover complete scoped handovers, evidence-held timelines, incident-specific audit, reference ownership, causal uncertainty, historical recovery labels, stress confusion matrices and sparse-data abstention. Node tests cover every module, rendering, payloads, tab-key logic, escaping, role controls and persistent errors. **They are not browser, DOM, layout or assistive-technology tests.**

Verification uses disposable databases. Existing local sessions are fingerprinted before and after the suite; detailed fingerprints are retained privately. The original saved database, its pre-improvement backup and all pre-existing rehearsals were preserved during repository preparation. Mutable data is excluded from the Git index.

## Manual browser acceptance still required

Start `python -m scripts.recording` (or `.\Start-Recording.cmd` on Windows). Use only the new session.

- [ ] Overview: default 86,880 units / 115 completed / 6 held; filters, empty cohort and CSV agree.
- [ ] Follow the [hero case](demo/hero_scenario.md) through both identities; after approval verify 87,600 / 116 / 5 held and incident-specific audit.
- [ ] Record Sam's INC-1043 plan with fill/pack references; leave its cause unknown and the case open. Confirm it leads Shift Handover and all five holds remain reachable.
- [ ] Inspect WO-2630 duplicates and held milestones; verify Data Trust reconciliation and historical recovery labeling.
- [ ] Inspect Method Lab false alerts, missed delays, threshold sensitivity and low-sample abstentions.
- [ ] Exercise forms by keyboard, visible focus, skip link, arrow-key tabs and inline errors; inspect 1920×1080, 1366×768, narrow width and 200% zoom.
- [ ] Test native export/import dialogs, feedback and restart persistence; inspect screen-reader behavior separately.
- [x] Inspect the supplied [authentic visual set](assets/README.md) for visible states, readability and personal information; distinguish the editorial comparison from screenshots.
- [ ] Rehearse the [recording script](demo/video_script.md) and complete the remaining live interaction checks.

The 16 November repository pass did not complete browser control. On 17 November, the supplied cropped PNGs were inspected directly: dashboard values agree with measured results, the operator proposal is pending, the supervisor recovery is approved before separate data-incident resolution, and the handover retains acknowledged, unresolved INC-1043. [Provenance](docs/ASSET_PROVENANCE.md) identifies the supplied source captures and crop boundaries. This static review does not constitute a new live browser journey. The architecture SVG remains an explanatory diagram; GitHub-hosted rendering has not been observed on a published repository.

## Readiness

The README now includes the authentic product showcase and is ready for local portfolio review. **Final screen-recording sign-off still requires browser acceptance and rehearsal.** GitHub Actions is configured but has not run on hosted infrastructure. Five non-hero seeded defects intentionally remain held; no arbitrary correction workflow or verified root cause is claimed.
