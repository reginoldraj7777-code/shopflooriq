# Hero scenario: one missing event, one real delay

## Start an isolated rehearsal

Every rehearsal should use a new database. Previous approvals, notes and audit history remain in their original sessions; no reset or migration is needed.

Run `python -m scripts.recording` from the project folder, or `.\Start-Recording.cmd` on Windows. Open http://127.0.0.1:8766. The launcher creates a unique file in `data/recordings/` and never overwrites a prior session. Use `--port 8767` if another recording server occupies 8766. Ctrl+C stops the server. To resume an existing rehearsal, use `python -m shopflooriq serve --db "data/recordings/<printed filename>.sqlite" --port 8766`.

Select Alex · operator. Use default seed 1042, last 14 days, all stations and all shifts. Reload the browser after restarting a server to obtain the current write token.

## Evidence

| Source | UTC time | Meaning |
|---|---|---|
| E-WO-1042-1 / R-WO-1042-1 | 15 Nov 06:00 | Order started |
| E-WO-1042-2 / R-WO-1042-2 | 15 Nov 06:30 | Filling finished |
| E-WO-1042-3 / R-WO-1042-3 | 15 Nov 08:50 | Packing began |
| BUF-1042 with E-WO-1042-4 / R-RECOVERY-1042 | Completed 09:10; receipt 09:12 | Separate 720-each completion receipt, initially absent from production staging |

Due 07:50 UTC; scenario clock 14:00. Naive age **480 minutes**; supported elapsed **190 minutes**; fill-to-pack interval **140 minutes**. These are different quantities. Timing does not establish a cause.

## Exact click path and prepared notes

1. **Mission Control → Investigate the signal.** Initial default scope: **86,880 units / 115 trusted completed / 6 held / 1 incomplete**. INC-1042 is open.
2. **Evidence & impact:** inspect the held timeline, missing completion and BUF-1042 JSON. Confirm matching order, event identity, unit, count and timestamps. The preview says **Not yet applied**.
3. **Human review**, Alex. Paste: `Reviewed WO-1042 timeline: completion is missing; BUF-1042 is available for identity and timestamp checks.` Click **Acknowledge & take ownership**.
4. Paste: `BUF-1042 matches WO-1042 and E-WO-1042-4: 720 each, completed 09:10 UTC and received 09:12. Propose recovery.` Click **Propose receipt recovery**. Metrics stay unchanged; Alex cannot approve.
5. Switch to **Sam · supervisor**. Paste: `Independently checked BUF-1042 order, count, unit and event times. Approve analytics evidence recovery; no product release.` Click **Approve recovery**.
6. Confirm **Applied with approval**, 720 units and 190 minutes. The completion milestone is **Recovered · approved**. The 140-minute wait remains. Paste: `Completion evidence restored and validated. Resolve data incident INC-1042; keep INC-1043 open for station-log investigation.` Click **Resolve data incident**.
7. **Audit trail:** inspect current-incident acknowledge/propose/approve/resolve with both actors and before/after evidence. Related operational audit is deliberately separate.
8. **Mission Control:** verify **87,600 units / 116 completed / 5 held / 1 incomplete / 94.4 min mean elapsed / 34.5% late share / 95.9% coverage**.
9. Open **INC-1043 → Human review**. As Sam, acknowledge with: `Reviewed fill at 06:30 and packing at 08:50. The 140-minute interval is observed; its cause remains undetermined.`
10. Record a structured plan. Next step: `Review the station log and compare material handoff timestamps with the observed packing start.` Missing information: `Station logs and material availability records are not included in this dataset, so the cause remains unknown.` Select **R-WO-1042-2** and **R-WO-1042-3**. Click **Record next step**. Do not close INC-1043 or claim that the proposed log review has occurred.
11. **Mission Control → Shift handover.** Confirm INC-1043 appears first, assigned to Sam, with the recorded step and references. Expand **Complete held-order register (5)**. All holds are present; planned-volume ranking does not claim actual production loss.

## Useful follow-up screens

- **WO-2630:** all recorded milestones are held, duplicate completion has two source copies, and duplicate/sequence findings are inspectable. There are no misleading green validation ticks.
- **Data Trust:** global contributors and exclusions reconcile; after recovery, the 480-minute comparison is explicitly historical.
- **Method Lab:** scroll to **Perfect on one seed is not enough**. Rare-deviation robust precision is 11.7%, low-sample baselines abstain, and threshold/error examples are expandable. These are synthetic stress results, not production accuracy.

The domain and real HTTP journey are automatically tested; JavaScript tests exercise rendered states and handlers in a Node VM. Complete the [browser checklist](../ACCEPTANCE.md) before recording: these tests do not establish layout, focus or native file-dialog behavior. No final video is supplied or published.
