"""Demo data: `python -m app.seed`. Bids go through the real service with back-dated clocks,
so the extensions and force-close you see were produced by the actual auction rules."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from . import service
from .auction import TriggerType
from .db import Base, SessionLocal, engine
from .models import Rfq
from .schemas import BidCreate, RfqCreate

MIN = timedelta(minutes=1)


def quote(carrier: str, freight: int, origin: int = 4500, dest: int = 3200, days: int = 24) -> dict:
    return dict(carrier_name=carrier, freight_charges=Decimal(freight), origin_charges=Decimal(origin),
                destination_charges=Decimal(dest), transit_days=days)


def scenario(db: Session, ref: str, name: str, start: datetime, close: datetime, forced: datetime,
             x: int, y: int, trigger: TriggerType, bids: list[tuple[int, dict]]) -> Rfq:
    """Create an auction, then replay its bids at `start + minutes`, each quote valid 30 days from when it was placed."""
    rfq = service.create_rfq(db, RfqCreate(
        reference_id=ref, name=name, pickup_date=close.date() + timedelta(7), bid_start_at=start,
        bid_close_at=close, forced_close_at=forced, trigger_window_minutes=x, extension_minutes=y,
        trigger_type=trigger), now=start - 60 * MIN)
    for minutes, q in bids:
        placed = start + minutes * MIN
        service.place_bid(db, rfq.id, BidCreate(**q, quote_valid_until=placed.date() + timedelta(30)), now=placed)
    return rfq


def live_auction(db: Session, now: datetime) -> Rfq:
    """An auction that closes in 5 minutes, with the extension window opening in 2."""
    return scenario(db, f"LIVE-{now:%m%d-%H%M%S}", "Nhava Sheva → Rotterdam · 2×40' HC",
                    now - 15 * MIN, now + 5 * MIN, now + 15 * MIN, 3, 2, TriggerType.L1_CHANGE,
                    [(2, quote("Maersk", 182000)), (5, quote("MSC", 176500, days=27)),
                     (9, quote("CMA CGM", 179000)), (13, quote("Maersk", 171000))])


def main() -> None:
    Base.metadata.create_all(engine)
    now = datetime.now(UTC).replace(microsecond=0)
    tag = f"{now:%m%d-%H%M}"
    with SessionLocal() as db:
        live_auction(db, now)
        scenario(db, f"FC-{tag}", "Chennai → Singapore · LCL 12 CBM", now - 90 * MIN, now - 40 * MIN, now - 25 * MIN,
                 10, 10, TriggerType.BID_RECEIVED,
                 [(10, quote("ONE", 64000, days=9)), (45, quote("Evergreen", 61500, days=11)),
                  (55, quote("ONE", 59900, days=9)), (62, quote("Evergreen", 58200, days=11))])
        scenario(db, f"CL-{tag}", "Delhi → Dubai · Air 850 kg", now - 300 * MIN, now - 180 * MIN, now - 120 * MIN,
                 10, 5, TriggerType.ANY_RANK_CHANGE,
                 [(20, quote("Emirates SkyCargo", 98000, days=2)), (40, quote("Qatar Cargo", 94500, days=3))])
        scenario(db, f"UP-{tag}", "Kolkata → Hamburg · 1×20' GP", now + 30 * MIN, now + 90 * MIN, now + 120 * MIN,
                 10, 5, TriggerType.BID_RECEIVED, [])
    print(f"Seeded demo auctions ({tag}).")


if __name__ == "__main__":
    main()
