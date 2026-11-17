"""Shared detector and deliberately imperfect, frozen synthetic stress protocol."""
from functools import lru_cache
from random import Random
from statistics import median


def fit(values):
    if not values:
        return None
    center = median(values)
    return dict(median=center, mad=median(abs(v-center) for v in values), n=len(values))


def score(value, baseline):
    if not baseline or baseline["n"] < 20:
        return None
    delta = value - baseline["median"]
    # A directional sentinel, NOT a z-score or probability when variance is zero.
    return .6745 * delta / baseline["mad"] if baseline["mad"] else (999 if delta > 0 else -999 if delta < 0 else 0)


def metrics(predictions, labels):
    pairs = [(p, y) for p, y in zip(predictions, labels) if p is not None]
    tp = sum(p and y for p,y in pairs)
    fp = sum(p and not y for p,y in pairs)
    fn = sum(not p and y for p,y in pairs)
    tn = sum(not p and not y for p,y in pairs)
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, evaluated=len(pairs), unavailable=len(labels)-len(pairs),
                positives=sum(labels), prevalence=sum(labels)/len(labels) if labels else None,
                precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None,
                false_positive_rate=fp/(fp+tn) if fp+tn else None)


CONDITIONS = [
    ("overlap", "Overlapping waits", "Ordinary variation overlaps small and large injected delays."),
    ("shift", "Benign operating shift", "Test-period normal waits shift +12 minutes; frozen training cannot adapt."),
    ("rare", "Rare deviations", "Only 1% injected deviations; ordinary long tails can dominate alerts."),
    ("zero", "Zero MAD", "Identical training waits; a one-minute normal departure triggers the sentinel."),
    ("small", "Low sample", "Only 12 training records; robust scoring must abstain."),
    ("tails", "Heavy normal tails", "Unlabeled long waits overlap injected delays; labels are simulation truth, not causes.")]


def stress_data(seed, condition):
    rng = Random(seed)
    # Protocol fixed before evaluation. Never search seeds or change labels to favor a detector.
    train = [30.0 if condition == "zero" else max(1, rng.gauss(30, 6))
             for _ in range(12 if condition == "small" else 120)]
    labels = [j % (100 if condition == "rare" else 10) == 0 for j in range(200)]
    test = []
    for label in labels:
        value = (30 + rng.choice([-1,0,0,1])) if condition == "zero" else max(1, rng.gauss(30, 6))
        if condition == "shift":
            value += 12
        if condition in {"tails", "rare"} and rng.random() < .08:
            value += rng.uniform(12, 40)
        if label:
            value += rng.uniform(8, 35)
        test.append(value)
    return train, test, labels


@lru_cache(maxsize=1)
def stress_evaluation():
    results = []
    examples = []
    for key, name, description in CONDITIONS:
        runs = [stress_data(seed, key) for seed in (11, 29, 47, 83, 101)]
        labels = [y for _, _, yy in runs for y in yy]
        values = [v for _, xx, _ in runs for v in xx]
        scores = []
        for train, test, _ in runs:
            baseline = fit(train)
            scores.extend(score(v, baseline) for v in test)
        thresholds = [dict(threshold=t, **metrics([None if s is None else s > t for s in scores], labels)) for t in (2.5,3.5,4.5)]
        fixed = metrics([v > 60 for v in values], labels)
        results.append(dict(key=key, name=name, description=description, thresholds=thresholds, fixed=fixed,
                            training_per_seed=len(runs[0][0]), testing=len(labels)))
        for outcome in ("false_positive", "false_negative"):
            candidates = [(j,v,s,y) for j,(v,s,y) in enumerate(zip(values,scores,labels))
                          if s is not None and ((s > 3.5 and not y) if outcome == "false_positive" else (s <= 3.5 and y))]
            if candidates:
                j,v,s,y = candidates[0]
                examples.append(dict(condition=key, outcome=outcome, seed=(11,29,47,83,101)[j//200],
                                     test_index=j%200, wait=round(v,2), score=round(s,2), label=y))
    return dict(protocol="stress-v1", seeds=[11,29,47,83,101], conditions=results, examples=examples,
                total_testing=sum(r["testing"] for r in results),
                chronology="Each run fits only its first training segment, then scores a separate future segment. Labels never enter fit or score. Thresholds are sensitivity checks, not selected on test results.")
