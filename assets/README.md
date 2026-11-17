# ShopfloorIQ visual gallery

The supplied `portfolio/` package contains **seven authentic application captures** and **one editorial comparison**. Every displayed order, identity and operation is synthetic. The images were inspected on **17 November 2026**; no image pixels were changed during README integration.

## Follow the evidence at full size

| Capture | What is visible |
|---|---|
| [Mission Control — before recovery](portfolio/dashboard-before.png) | 86,880 trusted units, 115 completed orders, 93.6-minute mean elapsed and 33.9% late share. |
| [Missing-event timeline](portfolio/missing-event-timeline.png) | Held milestones at 06:00 / 06:30 / 08:50, a missing completion and a 140-minute observed interval. |
| [BUF-1042 and impact preview](portfolio/recovery-evidence.png) | A synthetic receipt for 720 each, completion 09:10 UTC, 190 minutes elapsed; preview explicitly not yet applied. |
| [Operator proposal](portfolio/operator-proposal.png) | Alex's pending proposal; independent review required and self-approval disabled. |
| [Supervisor approval](portfolio/supervisor-approval.png) | Sam's approved recovery; INC-1042 remains acknowledged at revision 3, before separate resolution. |
| [Mission Control — after approval](portfolio/dashboard-after.png) | 87,600 units, 116 completed orders, 94.4-minute mean elapsed and 34.5% late share. The data review is still open. |
| [Evidence-linked Shift Handover](portfolio/evidence-linked-handover.png) | Sam owns acknowledged, unresolved INC-1043. The next step, missing information and evidence-reference count are visible; work completion is not verified. |

The seven PNG captures are **1906×947**. They show desktop viewports, including scrolled content; they are not full-page exports. The supplied provenance records removal of browser chrome and the Windows taskbar. No personal tabs or notifications are visible. The after-dashboard capture retains a harmless loopback link-status label. See [source mapping and crop notes](../docs/ASSET_PROVENANCE.md).

## Editorial and architecture visuals

- [Reporting before/after](portfolio/reporting-before-after.png), **1800×850**: an editorial comparison of readings from the genuine dashboard captures. It is **not an application screenshot**. The additional 720 units are restored reporting, not increased production.
- [Architecture](architecture.svg): an original diagram of the implemented data and approval flow, not a product capture. No external fonts, stock images or company logos are bundled.

## Verification boundary

Static captures document these visible states. They do not verify keyboard behavior, responsive layouts, file dialogs, audit-tab contents or a complete live interaction sequence. Separate audit-trail and Method Lab screenshots are not part of this package. The [browser acceptance checklist](../ACCEPTANCE.md) and [recording storyboard](../demo/video_script.md) remain relevant; no video is supplied or published.

To make new captures, use `python -m scripts.recording` and the [hero scenario](../demo/hero_scenario.md). This creates a separate session without resetting existing reviews. Keep synthetic labels, accurate captions and consistent sizing; preserve the supplied captures as evidence.
