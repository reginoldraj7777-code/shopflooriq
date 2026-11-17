"""Deterministic synthetic source; the labels are never detector inputs."""
from datetime import datetime, timedelta, timezone
import random

SEED = 1042
AS_OF = "2026-11-15T14:00:00+00:00"
HERO = "WO-1042"


def iso(value):
    return value.isoformat(timespec="seconds")


def generate(seed=SEED):
    rng = random.Random(seed)
    products = [{"id": "SKU-B250", "name": "Buffer solution · 250 mL", "target_minutes": 110},
                {"id": "SKU-R100", "name": "Reference reagent · 100 mL", "target_minutes": 100},
                {"id": "SKU-K050", "name": "Laboratory kit · 50 units", "target_minutes": 90}]
    stations = [{"id": "FILL-01", "name": "Manual filling"}, {"id": "PACK-02", "name": "Primary packaging"},
                {"id": "PACK-03", "name": "Kit assembly"}]
    orders, events, checks = [], [], []
    start = datetime(2026, 9, 5, tzinfo=timezone.utc)

    def add(oid, day, station, shift, sku, minutes, wait, label=False, state="closed"):
        t = day
        qty = rng.choice([600, 720, 840, 960])
        target = next(p["target_minutes"] for p in products if p["id"] == sku)
        order = dict(id=oid, station=station, shift=shift, product=sku, planned_units=qty,
                     start=iso(t), due=iso(t + timedelta(minutes=target)), state=state, label=label)
        orders.append(order)
        times = [t, t + timedelta(minutes=30), t + timedelta(minutes=30 + wait), t + timedelta(minutes=minutes)]
        for n, (kind, when) in enumerate(zip(["start", "fill", "pack", "complete"], times), 1):
            if state == "open" and n > 2:
                continue
            events.append(dict(row_id=f"R-{oid}-{n}", event_id=f"E-{oid}-{n}", order_id=oid,
                               station=station, kind=kind, event_time=iso(when),
                               ingested_at=iso(when + timedelta(minutes=2)), quantity=qty if n == 4 else 0,
                               unit="each", source="synthetic_mes"))
        checks.append(dict(id=f"QC-{oid}", order_id=oid, observation="Label alignment",
                           result="fail" if rng.random() < .035 else "pass", sampled_units=5))

    for day in range(72):
        for slot in range(9 if day < 71 else 3):
            station = stations[slot % 3]["id"]
            shift = ["Early", "Late", "Night"][slot // 3]
            t = start + timedelta(days=day, hours=5 + slot // 3 * 8, minutes=slot % 3 * 35)
            wait = max(8, round(rng.gauss(22 + slot % 3 * 5, 5)))
            label = day % 7 == 3 and slot in (1, 6)
            if label:
                wait += rng.choice([20, 28, 55])
            elif day in (60, 67) and slot == 4:
                wait += 18  # Unlabeled natural tail: a detector can produce false positives.
            minutes = 55 + wait + rng.randrange(4, 17)
            add(f"WO-{2000 + day * 9 + slot}", t, station, shift, products[slot % 3]["id"], minutes, wait, label)
    add(HERO, datetime(2026, 11, 15, 6, tzinfo=timezone.utc), "FILL-01", "Early", "SKU-B250", 190, 140, True)
    hero = orders[-1]
    hero["planned_units"] = 720
    recovery = events.pop()
    recovery.update(row_id="R-RECOVERY-1042", event_id="E-WO-1042-4", quantity=720, source="edge_buffer_recovery")
    # A deliberately absent transfer; the local buffer is evidence, not trusted production data.
    evidence = dict(id="BUF-1042", order_id=HERO, description="Synthetic edge buffer completion receipt", event=recovery)
    add("WO-OPEN-01", datetime(2026, 11, 15, 13, tzinfo=timezone.utc), "PACK-02", "Late", "SKU-R100", 95, 25, state="open")
    # Controlled defects are separate from operational anomaly labels.
    by_id = {e["event_id"]: e for e in events}
    duplicate = dict(by_id["E-WO-2630-4"], row_id="R-DUPLICATE-2630")
    events.append(duplicate)
    by_id["E-WO-2631-4"]["unit"] = "kg"
    by_id["E-WO-2632-3"]["event_time"] = "2026-11-14T04:00:00+00:00"
    by_id["E-WO-2628-4"]["quantity"] = -20
    by_id["E-WO-2629-2"]["ingested_at"] = "2026-11-15T12:00:00+00:00"
    return dict(seed=seed, as_of=AS_OF, products=products, stations=stations, orders=orders,
                events=events, checks=checks, evidence=[evidence])
