"""Pure British-auction rules. No I/O, no ORM: every function here is unit-testable in isolation.

Ranking works on any bid-like object exposing `carrier_name`, `total_amount` and `id`
(the ORM `Bid` in production, a simple tuple in tests).
"""

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol, Sequence


class TriggerType(StrEnum):
    BID_RECEIVED = "bid_received"
    ANY_RANK_CHANGE = "any_rank_change"
    L1_CHANGE = "l1_change"


class AuctionStatus(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    CLOSED = "closed"
    FORCE_CLOSED = "force_closed"


class BidLike(Protocol):
    id: int
    carrier_name: str
    total_amount: object  # Decimal in practice; only needs to be orderable


def rank[B: BidLike](bids: Sequence[B]) -> list[B]:
    """Each supplier's best bid, cheapest first (L1, L2, ...). Equal prices: earlier bid wins."""
    best: dict[str, B] = {}
    for bid in sorted(bids, key=lambda b: (b.total_amount, b.id)):
        best.setdefault(bid.carrier_name, bid)
    return list(best.values())  # dicts keep insertion order, which is already rank order


def status(now: datetime, start: datetime, close: datetime, forced_close: datetime) -> AuctionStatus:
    if now < start:
        return AuctionStatus.SCHEDULED
    if now < close:
        return AuctionStatus.ACTIVE
    # Extended all the way to the hard stop: bidding was cut off, not finished naturally.
    return AuctionStatus.FORCE_CLOSED if close >= forced_close else AuctionStatus.CLOSED


def in_trigger_window(now: datetime, close: datetime, window: timedelta) -> bool:
    return close - window <= now < close


def extension_reason(trigger: TriggerType, before: list[str], after: list[str]) -> str | None:
    """Why this bid should extend the auction, or None. `before`/`after` are supplier names in rank order.

    A newcomer landing at the bottom displaces nobody, so it is not a rank change.
    The first-ever bid creates an L1, so it counts as both an L1 change and a rank change.
    """
    l1_changed = before[:1] != after[:1]
    ranks_changed = l1_changed or after[: len(before)] != before

    match trigger:
        case TriggerType.BID_RECEIVED:
            return "Bid received in trigger window"
        case TriggerType.ANY_RANK_CHANGE if ranks_changed:
            return "Supplier ranking changed in trigger window"
        case TriggerType.L1_CHANGE if l1_changed:
            return f"New lowest bidder (L1): {after[0]}"
    return None


def extended_close(close: datetime, forced_close: datetime, extension: timedelta) -> datetime:
    """Push the close out by the extension, but never past the forced close."""
    return min(close + extension, forced_close)
