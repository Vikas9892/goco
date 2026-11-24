from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .auction import AuctionStatus, TriggerType
from .models import EventKind

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Charge = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Minutes = Annotated[int, Field(ge=1, le=180)]


# ---- Requests ---------------------------------------------------------------------------------


class RfqCreate(BaseModel):
    reference_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    pickup_date: date
    bid_start_at: AwareDatetime
    bid_close_at: AwareDatetime
    forced_close_at: AwareDatetime
    trigger_window_minutes: Minutes = 10
    extension_minutes: Minutes = 5
    trigger_type: TriggerType = TriggerType.BID_RECEIVED

    @model_validator(mode="after")
    def check_timeline(self) -> "RfqCreate":
        if self.bid_close_at <= self.bid_start_at:
            raise ValueError("Bid close time must be after bid start time")
        if self.forced_close_at <= self.bid_close_at:
            raise ValueError("Forced close time must be after bid close time")
        if self.pickup_date < self.bid_close_at.date():
            raise ValueError("Pickup / service date cannot be before bidding closes")
        return self


class BidCreate(BaseModel):
    carrier_name: Name
    freight_charges: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
    origin_charges: Charge = Decimal(0)
    destination_charges: Charge = Decimal(0)
    transit_days: Annotated[int, Field(ge=1, le=365)]
    quote_valid_until: date

    @property
    def total(self) -> Decimal:
        return (self.freight_charges + self.origin_charges + self.destination_charges).quantize(Decimal("0.01"))


# ---- Responses --------------------------------------------------------------------------------


class AuctionConfig(BaseModel):
    trigger_window_minutes: int
    extension_minutes: int
    trigger_type: TriggerType


class RfqSummary(BaseModel):
    id: int
    reference_id: str
    name: str
    status: AuctionStatus
    lowest_bid: Decimal | None
    bid_count: int
    bid_start_at: datetime
    bid_close_at: datetime
    forced_close_at: datetime


class RankedBid(BaseModel):
    rank: int
    id: int
    carrier_name: str
    freight_charges: Decimal
    origin_charges: Decimal
    destination_charges: Decimal
    total_amount: Decimal
    transit_days: int
    quote_valid_until: date
    created_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: EventKind
    message: str
    details: dict[str, Any]
    created_at: datetime


class AuctionStats(BaseModel):
    """Maps directly to the brief's success metrics: participation and price improvement."""

    bid_count: int
    supplier_count: int
    extension_count: int
    opening_price: Decimal | None
    current_price: Decimal | None
    savings_percent: float | None


class RfqDetail(BaseModel):
    id: int
    reference_id: str
    name: str
    pickup_date: date
    status: AuctionStatus
    bid_start_at: datetime
    original_close_at: datetime
    bid_close_at: datetime
    forced_close_at: datetime
    config: AuctionConfig
    ranking: list[RankedBid]
    events: list[EventOut]  # newest first
    stats: AuctionStats
    server_time: datetime  # lets clients correct their countdown for local clock drift
