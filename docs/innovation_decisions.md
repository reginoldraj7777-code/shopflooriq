# Innovation shortlist and choices

The early shortlist ranked ideas by role relevance, ability to substantiate behavior, demo impact, clarity and implementation cost. Scores below are product judgments (1 low, 5 high), not measured business results. Cost 5 means expensive.

| Rank | Candidate | Relevance | Proof | Demo | Clarity | Cost | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | Before/after reporting-impact preview tied to a source receipt | 5 | 5 | 5 | 5 | 2 | Implemented |
| 2 | Source-linked deterministic shift handover | 5 | 5 | 4 | 5 | 2 | Implemented |
| 3 | Separate data uncertainty and operational investigations for the same order | 5 | 5 | 5 | 5 | 2 | Implemented |
| 4 | Evidence coverage alongside KPI denominators | 5 | 5 | 4 | 5 | 1 | Implemented |
| 5 | Chronological rules-versus-MAD comparison with row drill-down | 5 | 5 | 4 | 4 | 3 | Implemented |
| 6 | Animated event replay with time scrubber | 4 | 4 | 5 | 3 | 4 | Not selected; static observed timeline is easier to inspect |
| 7 | Counterfactual station-capacity / staffing simulator | 4 | 2 | 4 | 3 | 5 | Not selected; source data cannot support causal capacity claims |
| 8 | LLM assistant for investigation summaries | 3 | 2 | 4 | 3 | 4 | Not selected; deterministic evidence summary does the useful part |
| 9 | Mobile scanner and offline operator event capture | 4 | 3 | 4 | 4 | 5 | Not selected; much larger synchronization/error-handling surface |
| 10 | Full defect taxonomy and arbitrary event supersession workflow | 5 | 5 | 3 | 3 | 5 | Documented extension; focused reviewed recovery is implemented |

## Selected improvement 1: preview the actual reporting consequence

INC-1042 shows **480 minutes of naive age**, **190 minutes of supported elapsed time** and **+720 trusted units** if the receipt is approved. It explicitly distinguishes preview from applied state. Approval changes the same facts used by charts and exports, not a separate demonstration counter.

This is useful because a reviewer sees what will change before acting, and learns that more complete evidence may worsen a headline metric. The late-order share rises from 33.9% to 34.5%; the interface does not spin a data correction into an operational improvement. The tradeoff is a narrow, well-supported hero recovery rather than a generalized data-editing console.

## Selected improvement 2: an evidence-backed handover

The handover summarizes the current filter cohort’s completed units, held/incomplete population, late-order denominator and open incidents with owner/state. CSV and incident links make every statement inspectable. It is generated on demand from current API state, with no LLM, network call or invented root cause.

This connects historical analytics to a practical shift transition and gives a technical reviewer a concise way to examine both communication and calculation. The tradeoff is that it is an in-app summary, not an external message or formal electronic shift sign-off.

## Supporting decisions

Separate incidents prevent a successful data repair from falsely closing a genuine wait investigation. Coverage and denominator labels distinguish data availability from operational performance. The holdout lab makes tool evaluation reproducible rather than rhetorical. Each choice is grounded in source records and tested behavior; none claims actual manufacturer outcomes or savings.

## Three improvements selected in the comprehensive pass

1. **Evidence-linked next-step register.** A reviewer can record a concrete next action, missing information and references that the server verifies belong to the order. It appears in the current incident and complete shift handover with author/audit provenance. This solves the lost-context problem without inventing an action or interpreting a free-text note as proof of completion. Existing reviews need no migration or backfill.
2. **Detector stress workbench.** Six conditions, five fixed seeds, threshold sensitivity, explicit abstentions and inspectable false alerts/misses challenge the attractive perfect seed result. This solves a responsible-tool-evaluation problem: a reviewer can see how normal shifts and rare events break an apparently excellent detector. It does not add opaque AI or require new runtime dependencies.
3. **Separate recording sessions.** A one-command launcher exclusively creates a uniquely named database. This solves the conflict between repeatable rehearsals and preserving real review work within the synthetic application. It costs additional small SQLite files, which the user can retain; it never resets the working database.

The rest of this pass fixes correctness and usability: complete handover coverage, incident-specific audit and review, closure safeguards, held timeline states, global KPI reconciliation, historical recovery labelling, keyboard tab behavior and persistent inline errors. These are quality fixes, not additional speculative features.
