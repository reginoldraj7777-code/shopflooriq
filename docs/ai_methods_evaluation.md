# Grounded analytical-tool evaluation

The core demo requires no paid key or external AI service. “AI-tool evaluation” is represented by a reproducible comparison of two explainable detection approaches, not an ornamental chatbot. Both prioritize longer fill-to-pack waits for human investigation. Neither claims causal discovery.

## Methods

1. **Fixed operational rule:** signal if fill-to-pack wait is strictly greater than 60 minutes. No fitted parameters; explanation is the observed wait and threshold.
2. **Station-aware robust score:** fit the median wait and median absolute deviation (MAD) separately per station using the earlier training period. Score `0.6745 × (wait − median) / MAD`; flag the upper tail above 3.5.

NIST describes median/MAD modified z-scores and the conventional magnitude 3.5 outlier threshold. ShopfloorIQ deliberately uses the **upper tail only**, because this use case concerns extended waits. This is an engineering choice, not a universal statistical guarantee. Reference: [NIST, Detection of Outliers](https://itl.nist.gov/div898/handbook/eda/section3/eda35h.htm).

At least 20 trusted training orders per station are required. When the baseline is missing or insufficient, robust scoring is unavailable and excluded from that method’s confusion matrix; the number unavailable is shown. With zero MAD, exact-center observations score 0 and departures use signed sentinel ±999. Only positive departures are flagged; the sentinel is not a calibrated z-score.

## Experiment

Default seed 1042, before hero recovery:

- 72 scenario days and 644 total orders.
- 637 trusted closed orders; 6 held and 1 incomplete excluded from detector evaluation.
- Training: order start before **2026-10-23**, **432 orders**.
- Held-out period: start on/after **2026-10-23**, **205 orders**, **6 planted positive examples**.
- Baselines: FILL-01 median 22 min / MAD 3.5; PACK-02 median 28 / MAD 3.5; PACK-03 median 32 / MAD 4. Each has 144 training orders.
- Operational labels are generator metadata used only to score detection quality. No label or held-out value enters the fitted baseline.

| Approach | TP | FP | FN | TN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| Fixed >60-min rule | 3 | 0 | 3 | 199 | 100% | 50% |
| Station median/MAD | 6 | 0 | 0 | 199 | 100% | 100% |

Precision = TP/(TP+FP); recall = TP/(TP+FN). Undefined denominators return null. Metrics are recomputed from current trusted facts. Recovering WO-1042 adds one labeled, long-wait order to the held-out population, so the live results change; the table above is explicitly the initial state.

Reproduce the fresh initial comparison with `python -m scripts.benchmark`, which uses an isolated temporary database, or read [measured_results.json](measured_results.json). `python -m shopflooriq evaluate --db <session-path>` evaluates the current state of a specific session, including any approved recovery. Tests reconcile confusion matrices, ensure label changes cannot change scores, ensure held-out values cannot change the training baselines, and cover zero MAD and absent training cohorts.

## What can be concluded

The adaptive threshold finds planted moderate deviations that a fixed 60-minute threshold misses. Its per-station baseline makes the signal explainable to an operations reviewer. The rule is simpler to communicate and could be useful for a hard operational boundary. Neither approach needs an opaque model to establish this small workflow.

This comparison is **not an unbiased estimate of production accuracy**. The synthetic generator was deliberately revised after an initial trivial comparison so that the methods had a useful distinction. The resulting seed is therefore a demonstration fixture, not a pristine independent benchmark. Its six held-out positives, limited station patterns and simplified labels make perfect precision easy to overinterpret. No confidence interval or generalization claim is warranted.

The additional stress protocol below addresses multiple operating conditions and explicit failure modes. A future prospective study would still need operator-reviewed label definitions and stratification by SKU/shift. No private company data is needed for this demonstration.

## Additional stress protocol: stress-v1

Implemented in `shopflooriq/methods.py` and displayed in Method Lab. Seeds are fixed at **11, 29, 47, 83, 101**, with 120 earlier training observations and 200 separate future observations per seed (12 training observations for the low-sample condition). Six conditions produce **6,000 scored or explicitly unavailable future observations**. The original production generator and labels were not changed by this improvement pass.

Each run represents one station distribution. Normal waits use a 30-minute center with 6-minute standard deviation. Labels mark an injected 8–35-minute delay every tenth observation, or every hundredth in the rare-deviation condition. These label criteria are fixed before scoring; no seed search or threshold optimization is performed. Injected delays overlap normal variation. Benign shift adds 12 minutes only to the future segment; rare/tail cases also contain unlabeled long waits; zero-MAD training is constant with ±1-minute ordinary future variation. The low-sample detector abstains.

This is a transparent robustness experiment designed by the application author, not an externally held-out factory benchmark. Reusing the same seeds across conditions makes comparisons inspectable; it does not make conditions statistically independent replications.

Pooled results at robust threshold **3.5**, measured 16 November 2026:

| Condition | Positives / future n | Robust TP / FP / FN / TN | Precision | Recall | Unscored |
|---|---:|---|---:|---:|---:|
| Overlapping waits | 100 / 1,000 | 52 / 1 / 48 / 899 | 98.1% | 52.0% | 0 |
| Benign operating shift | 100 / 1,000 | 86 / 71 / 14 / 829 | 54.8% | 86.0% | 0 |
| Rare deviations | 10 / 1,000 | 7 / 53 / 3 / 937 | 11.7% | 70.0% | 0 |
| Zero MAD | 100 / 1,000 | 100 / 228 / 0 / 672 | 30.5% | 100% | 0 |
| Low sample | 100 / 1,000 | 0 / 0 / 0 / 0 | undefined | undefined | 1,000 |
| Heavy normal tails | 100 / 1,000 | 57 / 56 / 43 / 844 | 50.4% | 57.0% | 0 |

Method Lab also displays the fixed-rule matrix for every condition, false-positive rate `FP/(FP+TN)`, thresholds **2.5 / 3.5 / 4.5**, and the first observed example of each available false-positive/false-negative type with reproducible seed and future index. All results are in [measured_results.json](measured_results.json), under `evaluation.stress`. Precision and recall use the standard definitions documented by [scikit-learn](https://scikit-learn.org/stable/modules/model_evaluation.html#precision-recall-f-measure-metrics); scikit-learn is a reference, not a runtime dependency.

The practical implications are limited but useful: a modest benign shift can create many alerts; low prevalence makes precision fragile; high recall with zero MAD conceals 228 false alerts; abstention must not look like perfect accuracy. We retain the original threshold for demonstration rather than pick a winner after inspecting this test set. Neither the outlier score nor the injected-delay label identifies a real-world cause. NIST's [outlier guidance](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm) likewise treats unusual observations as investigation candidates and notes dependence on distributional assumptions. Sources checked during this pass.

## Optional LLM considered, not used

An LLM incident summary could paraphrase evidence but would add evaluation, provenance and hallucination risks without improving the demonstrated calculation. The handover is instead deterministic, links directly to records and stays fully offline. No generated claim is mistaken for an observed cause.
