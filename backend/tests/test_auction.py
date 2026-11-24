from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import NamedTuple

from app.auction import AuctionStatus, TriggerType, extended_close, extension_reason, in_trigger_window, rank, status

T0 = datetime(2026, 1, 1, 18, 0, tzinfo=UTC)
MIN = timedelta(minutes=1)


class B(NamedTuple):
    id: int
    carrier_name: str
    total_amount: Decimal


def names(bids):
    return [b.carrier_name for b in rank(bids)]


def test_rank_uses_each_suppliers_best_bid_and_earlier_bid_wins_ties():
    bids = [B(1, "A", Decimal(100)), B(2, "B", Decimal(90)), B(3, "A", Decimal(80)), B(4, "C", Decimal(90))]
    assert names(bids) == ["A", "B", "C"]
    assert rank(bids)[0].total_amount == 80


def test_status_lifecycle():
    start, close, forced = T0 - 60 * MIN, T0, T0 + 30 * MIN
    assert status(start - MIN, start, close, forced) is AuctionStatus.SCHEDULED
    assert status(close - MIN, start, close, forced) is AuctionStatus.ACTIVE
    assert status(close, start, close, forced) is AuctionStatus.CLOSED
    assert status(forced, start, forced, forced) is AuctionStatus.FORCE_CLOSED


def test_trigger_window_is_inclusive_of_start_exclusive_of_close():
    assert in_trigger_window(T0 - 10 * MIN, T0, 10 * MIN)
    assert not in_trigger_window(T0 - 10 * MIN - timedelta(seconds=1), T0, 10 * MIN)
    assert not in_trigger_window(T0, T0, 10 * MIN)


def test_extension_never_passes_forced_close():
    assert extended_close(T0, T0 + 30 * MIN, 5 * MIN) == T0 + 5 * MIN
    assert extended_close(T0, T0 + 2 * MIN, 5 * MIN) == T0 + 2 * MIN


def test_bid_received_always_triggers():
    assert extension_reason(TriggerType.BID_RECEIVED, ["A", "B"], ["A", "B"])


def test_rank_change_trigger():
    t = TriggerType.ANY_RANK_CHANGE
    assert extension_reason(t, ["A", "B"], ["B", "A"])  # overtake
    assert extension_reason(t, ["A", "B"], ["A", "C", "B"])  # newcomer pushes B down
    assert not extension_reason(t, ["A", "B"], ["A", "B", "C"])  # newcomer at the bottom displaces nobody
    assert not extension_reason(t, ["A", "B"], ["A", "B"])  # A cut price but kept L1


def test_l1_trigger_fires_only_when_lowest_bidder_changes():
    t = TriggerType.L1_CHANGE
    assert extension_reason(t, [], ["A"])  # first bid creates an L1
    assert extension_reason(t, ["A", "B"], ["B", "A"])
    assert not extension_reason(t, ["A", "B", "C"], ["A", "C", "B"])  # L2/L3 swap only
