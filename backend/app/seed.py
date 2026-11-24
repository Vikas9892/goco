"""Demo data: `python -m app.seed`. Bids go through the real service with back-dated clocks,
so the extensions and force-close you see were produced by the actual auction rules."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from . import service
from .auction import TriggerType
from .db import Base, SessionLocal, engine
from .schemas import BidCreate, RfqCreate

MIN = timedelta(minutes=1)


def quote(carrier: str, freight: int, origin: int = 4500, dest: int = 3200, days: int = 24) -> BidCreate:
    return BidCreate(carrier_name=carrier, freight_charges=Decimal(freight), origin_charges=Decimal(origin),
                     destination_charges=Decimal(dest), transit_days=days, quote_valid_until=date.today() + timedelta(30))


def main() -> None:
    Base.metadata.create_all(engine)
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    tag = now.strftime("%m%d-%H%M")  # unique refs, so seeding twice never collides
    scenarios = [
        # (ref, name, start, close, forced, X, Y, trigger, [(minutes after start, quote)])
        (f"LIVE-{tag}", "Nhava Sheva → Rotterdam · 2×40' HC", now - 20 * MIN, now + 6 * MIN, now + 20 * MIN,
         5, 3, TriggerType.L1_CHANGE,
         [(2, quote("Maersk", 182000)), (5, quote("MSC", 176500, days=27)), (9, quote("CMA CGM", 179000)),
          (14, quote("Maersk", 171000))]),
        (f"FC-{tag}", "Chennai → Singapore · LCL 12 CBM", now - 90 * MIN, now - 40 * MIN, now - 25 * MIN,
         10, 10, TriggerType.BID_RECEIVED,
         [(10, quote("ONE", 64000, days=9)), (45, quote("Evergreen", 61500, days=11)),
          (55, quote("ONE", 59900, days=9)), (62, quote("Evergreen", 58200, days=11))]),
        (f"CL-{tag}", "Delhi → Dubai · Air 850 kg", now - 5 * 60 * MIN, now - 3 * 60 * MIN, now - 2 * 60 * MIN,
         10, 5, TriggerType.ANY_RANK_CHANGE,
         [(20, quote("Emirates SkyCargo", 98000, days=2)), (40, quote("Qatar Cargo", 94500, days=3))]),
        (f"UP-{tag}", "Kolkata → Hamburg · 1×20' GP", now + 30 * MIN, now + 90 * MIN, now + 120 * MIN,
         10, 5, TriggerType.BID_RECEIVED, []),
    ]

    with SessionLocal() as db:
        for ref, name, start, close, forced, x, y, trigger, bids in scenarios:
            rfq = service.create_rfq(db, RfqCreate(
                reference_id=ref, name=name, pickup_date=close.date() + timedelta(7), bid_start_at=start,
                bid_close_at=close, forced_close_at=forced, trigger_window_minutes=x, extension_minutes=y,
                trigger_type=trigger), now=start - 60 * MIN)
            for minutes, q in bids:
                service.place_bid(db, rfq.id, q, now=start + minutes * MIN)
    print(f"Seeded {len(scenarios)} demo auctions ({tag}).")


if __name__ == "__main__":
    main()
