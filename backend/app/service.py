"""Use-cases: each function is one transaction. Rules live in `auction.py`; this module applies them to the DB."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import auction
from .auction import AuctionStatus
from .models import AuctionEvent, Bid, EventKind, Rfq
from .schemas import AuctionConfig, AuctionStats, BidCreate, RankedBid, RfqCreate, RfqDetail, RfqSummary


class AuctionError(Exception):
    """A business-rule violation. The message is safe to show to end users."""

    status_code = 400


class RfqNotFound(AuctionError):
    status_code = 404


class BidRejected(AuctionError):
    status_code = 409


class DuplicateReference(AuctionError):
    status_code = 409


def _status(rfq: Rfq, now: datetime) -> AuctionStatus:
    return auction.status(now, rfq.bid_start_at, rfq.bid_close_at, rfq.forced_close_at)


def _supplier_order(bids: list[Bid]) -> list[str]:
    return [b.carrier_name for b in auction.rank(bids)]


def _log(rfq: Rfq, kind: EventKind, message: str, now: datetime, **details) -> None:
    rfq.events.append(AuctionEvent(kind=kind, message=message, details=details, created_at=now))


# ---- Commands ---------------------------------------------------------------------------------


def create_rfq(db: Session, data: RfqCreate, now: datetime) -> Rfq:
    rfq = Rfq(
        **data.model_dump(exclude={"bid_close_at"}),
        bid_close_at=data.bid_close_at,
        original_close_at=data.bid_close_at,
        created_at=now,
    )
    _log(rfq, EventKind.RFQ_CREATED, "RFQ created with British Auction enabled", now)
    db.add(rfq)
    try:
        db.commit()
    except IntegrityError:  # unique constraint is the source of truth, so concurrent creates are safe too
        db.rollback()
        raise DuplicateReference(f"RFQ reference '{data.reference_id}' already exists") from None
    return rfq


def place_bid(db: Session, rfq_id: int, data: BidCreate, now: datetime) -> Rfq:
    # Lock the auction row: bids on one RFQ are serialised, so two simultaneous bids can never
    # both read the same ranking or race to extend the close time. (No-op on SQLite, which locks the whole DB.)
    rfq = db.scalar(select(Rfq).where(Rfq.id == rfq_id).with_for_update())
    if rfq is None:
        raise RfqNotFound(f"RFQ {rfq_id} not found")

    if (state := _status(rfq, now)) is not AuctionStatus.ACTIVE:
        raise BidRejected(f"Auction is {state.value.replace('_', ' ')}; bids are not accepted")
    if data.quote_valid_until < now.date():
        raise BidRejected("Quote validity date is already in the past")

    own_best = min((b.total_amount for b in rfq.bids if b.carrier_name == data.carrier_name), default=None)
    if own_best is not None and data.total >= own_best:
        raise BidRejected(f"New bid must be lower than your previous best of {own_best:,.2f}")

    before = _supplier_order(rfq.bids)
    bid = Bid(**data.model_dump(), total_amount=data.total, created_at=now)
    rfq.bids.append(bid)
    db.flush()  # assigns bid.id, which ranking uses as the tie-breaker
    after = _supplier_order(rfq.bids)

    position = after.index(data.carrier_name) + 1
    _log(rfq, EventKind.BID_PLACED, f"{data.carrier_name} bid {data.total:,.2f} (now L{position})", now,
         carrier=data.carrier_name, amount=str(data.total), rank=position)

    _maybe_extend(rfq, before, after, now)
    db.commit()
    return rfq


def _maybe_extend(rfq: Rfq, before: list[str], after: list[str], now: datetime) -> None:
    window = timedelta(minutes=rfq.trigger_window_minutes)
    if not auction.in_trigger_window(now, rfq.bid_close_at, window):
        return
    reason = auction.extension_reason(rfq.trigger_type, before, after)
    if reason is None:
        return

    old_close = rfq.bid_close_at
    new_close = auction.extended_close(old_close, rfq.forced_close_at, timedelta(minutes=rfq.extension_minutes))
    if new_close == old_close:
        return  # already at the forced close: nothing left to extend

    capped = new_close == rfq.forced_close_at
    rfq.bid_close_at = new_close
    _log(rfq, EventKind.TIME_EXTENDED,
         f"{reason}; close extended by {(new_close - old_close) / timedelta(minutes=1):g} min"
         + (" (capped at forced close)" if capped else ""),
         now, reason=reason, old_close_at=old_close.isoformat(), new_close_at=new_close.isoformat(), capped=capped)


# ---- Queries ----------------------------------------------------------------------------------


def get_rfq(db: Session, rfq_id: int) -> Rfq:
    if (rfq := db.get(Rfq, rfq_id)) is None:
        raise RfqNotFound(f"RFQ {rfq_id} not found")
    return rfq


def list_rfqs(db: Session, now: datetime) -> list[RfqSummary]:
    totals = (
        select(Bid.rfq_id, func.min(Bid.total_amount).label("lowest"), func.count().label("bids"))
        .group_by(Bid.rfq_id)
        .subquery()
    )
    rows = db.execute(
        select(Rfq, totals.c.lowest, totals.c.bids)
        .outerjoin(totals, totals.c.rfq_id == Rfq.id)
        .order_by(Rfq.bid_close_at.desc())
    )
    return [
        RfqSummary(
            id=rfq.id, reference_id=rfq.reference_id, name=rfq.name, status=_status(rfq, now),
            lowest_bid=lowest, bid_count=bids or 0, bid_start_at=rfq.bid_start_at,
            bid_close_at=rfq.bid_close_at, forced_close_at=rfq.forced_close_at,
        )
        for rfq, lowest, bids in rows
    ]


def _columns(row: Rfq | Bid) -> dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}


def rfq_detail(rfq: Rfq, now: datetime) -> RfqDetail:
    ranking = auction.rank(rfq.bids)
    opening = rfq.bids[0].total_amount if rfq.bids else None
    current = ranking[0].total_amount if ranking else None

    return RfqDetail(
        **_columns(rfq),
        status=_status(rfq, now),
        config=AuctionConfig.model_validate(rfq, from_attributes=True),
        ranking=[RankedBid(rank=i, **_columns(b)) for i, b in enumerate(ranking, start=1)],
        events=list(reversed(rfq.events)),
        stats=AuctionStats(
            bid_count=len(rfq.bids),
            supplier_count=len(ranking),
            extension_count=sum(e.kind is EventKind.TIME_EXTENDED for e in rfq.events),
            opening_price=opening,
            current_price=current,
            savings_percent=round(float((opening - current) / opening * 100), 1) if opening else None,
        ),
        server_time=now,
    )
