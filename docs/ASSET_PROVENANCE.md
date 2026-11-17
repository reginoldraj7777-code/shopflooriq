# Authentic screenshot provenance

The supplied package identifies all seven application screenshots in `assets/portfolio/` as user-provided ShopfloorIQ captures. Its documented edits were **cropping away Microsoft Edge tabs/address bar and Windows taskbar**; application controls, identities, labels, figures, dates and statuses were preserved. `reporting-before-after.png` is a separately labeled editorial comparison using readings visible in the actual application screenshots; it is not an application screenshot. All data are synthetic. The original source filenames below date the captures to 16 November 2026.

## Source mapping

- **assets/portfolio/dashboard-before.png** — Before: 86,880 trusted units, 115 completed orders, INC-1042 outstanding. Source: `image(20261116-182805).png`. Crop external browser chrome (top 80 px) and Windows taskbar (below y=1027); no UI elements altered.
- **assets/portfolio/missing-event-timeline.png** — Before: held evidence, missing completion, 140-minute observed interval. Source: `image(20261116-182853).png`. Crop external browser chrome (top 80 px) and Windows taskbar (below y=1027); no UI elements altered.
- **assets/portfolio/recovery-evidence.png** — BUF-1042: independent synthetic receipt; 09:10 UTC; 720 units; 190 minutes. Source: `image(20261116-183311).png`. Crop external browser chrome (top 80 px) and Windows taskbar (below y=1027); no UI elements altered.
- **assets/portfolio/operator-proposal.png** — Alex Morgan: proposal pending, self-approval disabled. Source: `image(20261116-183425).png`. Crop external browser chrome (top 80 px) and Windows taskbar (below y=1027); no UI elements altered.
- **assets/portfolio/supervisor-approval.png** — Sam Chen: approved BUF-1042, incident revision 3. Source: `image(20261116-183553).png`. Crop external browser chrome (top 80 px) and Windows taskbar (below y=1027); no UI elements altered.
- **assets/portfolio/dashboard-after.png** — After: 87,600 trusted units, 116 completed orders, incident still under review. Source: `image(20261116-183636).png`. Crop external browser chrome (top 80 px) and Windows taskbar (below y=1027); no UI elements altered.
- **assets/portfolio/evidence-linked-handover.png** — After: INC-1043 acknowledged and unresolved, with Sam Chen assigned and an evidence-linked next action. Source: `image(20261116-184443).png`. Crop external browser chrome (top 80 px) and Windows taskbar (below y=1027); no UI elements altered.
- **assets/portfolio/reporting-before-after.png** — Editorial comparison graphic using the verified KPI readings shown in the genuine application screenshots. Not itself a screenshot. Source: `Derived solely from verified before and after dashboard screenshots`. Composed comparison with labels; no fabricated product UI or metrics.

## Repository review — 17 November 2026

All eight supplied PNGs were opened and visually inspected. The application captures are 1906×947; the editorial comparison is 1800×850. No personal browser tabs, notifications, real factory records or company branding are visible. `dashboard-after.png` retains a loopback link-status label. The scrolled receipt capture shows its synthetic source in the JSON even though the page header is outside the viewport. These are viewport captures, not full-page exports.

The visible 86,880 → 87,600 units, 115 → 116 orders, 93.6 → 94.4 mean minutes, 33.9% → 34.5% late share and 95.0% → 95.9% coverage agree with the [measured scenario](measured_results.json). Approval is visibly separate from data-incident resolution: the approved screen still shows INC-1042 acknowledged at revision 3. The later handover shows INC-1043 acknowledged, its cause unestablished and the planned work not verified as complete.

No pixels were edited during README integration. This review checks the supplied cropped files and documented provenance; it does not independently reconstruct the crop history or certify the complete live workflow. See the [gallery](../assets/README.md) and [remaining browser checks](../ACCEPTANCE.md).
