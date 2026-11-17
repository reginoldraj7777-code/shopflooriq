# Metric contract and reconciliation

All production KPIs use **trusted closed orders only**: a closed source order with all required milestones and no blocking validation finding on any of its source rows. Quarantine is order-level. No source repair, arbitrary deduplication, zero-filling or imputed completion contributes to reporting.

| Metric | Numerator / computation | Denominator | Missing/suspect treatment |
|---|---|---|---|
| Trusted throughput | Sum of completion-event `quantity` in each | None; a count in the selected order cohort, not units/hour | Entire held/incomplete orders excluded |
| Mean elapsed time | Sum of `(complete − start)` in minutes | Number of trusted closed orders | Excluded, never age-to-clock substituted |
| Late-order share | Trusted orders with complete strictly after planned due | All trusted closed orders | Unknown schedule status for held/incomplete work; exact due is on time |
| Check pass rate | Passing quality observations linked to trusted orders | All recorded checks linked to trusted orders | Held/incomplete order checks excluded; not unit yield/defect rate |
| Closed-order coverage | Number of trusted closed orders | All closed source orders, including held ones | Open work is outside denominator; not statistical confidence |
| Fill-to-pack wait | Pack-start timestamp minus fill-finish timestamp | Per-order value | Detector uses trusted closed orders only |

Empty populations: unit count is 0; mean, shares and coverage are null and display “—”. Percentages are rounded to one decimal for presentation. The calculation uses the underlying counts, not averages of subgroup percentages. Mean elapsed weights orders equally, not by quantity.

## Scope

Date/station/shift filters are combined with AND. Dates refer to **order start date in UTC**, not completion date; midnight-crossing orders stay in their starting cohort. Trends and station summaries share the same filtered fact rows. This is a cohort view, not calendar-day shipment accounting.

CSV export includes every trusted order in those period/station/shift filters. Search, evidence-state filter and pagination are UI exploration tools and do not narrow that export. Data Trust and Method Lab use the entire source scenario and say so explicitly.

Observed completion is compared with the synthetic SKU target embodied by planned `due`. There is no OEE, machine availability, savings, real capacity, certified yield or ROI metric.

## Reconciliation evidence

Tests independently sum valid completion events in raw JSON, persisted SQL `SUM(units)`, returned metrics, daily series and station summaries. A hand-calculated two-order fixture tests elapsed mean, late share, check denominator and closed-order coverage. Separate tests verify empty sets and combined filters.

For default seed 1042, last 14 scenario days:

| Metric | Before recovery | After independent approval |
|---|---:|---:|
| Total source orders in scope | 122 | 122 |
| Trusted closed orders | 115 | 116 |
| Held orders | 6 | 5 |
| Incomplete orders | 1 | 1 |
| Trusted units | 86,880 | 87,600 |
| Mean elapsed, minutes | 93.6 | 94.4 |
| Late trusted orders | 39 | 40 |
| Late share | 33.9% | 34.5% |
| Check pass rate | 110 / 115 = 95.7% | 111 / 116 = 95.7% |
| Closed-order coverage | 115 / 121 = 95.0% | 116 / 121 = 95.9% |

WO-1042’s naive age is **480 min** from 06:00 to the 14:00 scenario clock. Its reviewed completion at 09:10 establishes **190 min** elapsed; its due time was **07:50**, so it remains late. Recovering evidence improves coverage while legitimately increasing the late-order share. The original source rows and the review history remain intact.
