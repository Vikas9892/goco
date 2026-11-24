from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .auction import TriggerType
from .db import Base, UTCDateTime

Money = Numeric(12, 2)


def _enum(cls: type[StrEnum]) -> Enum:
    # Store the readable value ("l1_change"), as a VARCHAR + CHECK, so adding a member needs no type migration.
    return Enum(cls, native_enum=False, length=30, values_callable=lambda e: [m.value for m in e])


class EventKind(StrEnum):
    RFQ_CREATED = "rfq_created"
    BID_PLACED = "bid_placed"
    TIME_EXTENDED = "time_extended"


class Rfq(Base):
    __tablename__ = "rfqs"
    __table_args__ = (
        CheckConstraint("bid_start_at < original_close_at", name="ck_rfq_start_before_close"),
        CheckConstraint("original_close_at < forced_close_at", name="ck_rfq_forced_after_close"),
        CheckConstraint("bid_close_at <= forced_close_at", name="ck_rfq_never_past_forced_close"),
        CheckConstraint("trigger_window_minutes > 0 AND extension_minutes > 0", name="ck_rfq_positive_config"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_id: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    pickup_date: Mapped[date]

    bid_start_at: Mapped[datetime] = mapped_column(UTCDateTime)
    original_close_at: Mapped[datetime] = mapped_column(UTCDateTime)
    bid_close_at: Mapped[datetime] = mapped_column(UTCDateTime)  # moves forward with each extension
    forced_close_at: Mapped[datetime] = mapped_column(UTCDateTime)

    trigger_window_minutes: Mapped[int]  # X
    extension_minutes: Mapped[int]  # Y
    trigger_type: Mapped[TriggerType] = mapped_column(_enum(TriggerType))

    created_at: Mapped[datetime] = mapped_column(UTCDateTime)

    bids: Mapped[list["Bid"]] = relationship(back_populates="rfq", order_by="Bid.id", cascade="all, delete-orphan")
    events: Mapped[list["AuctionEvent"]] = relationship(order_by="AuctionEvent.id", cascade="all, delete-orphan")


class Bid(Base):
    __tablename__ = "bids"
    __table_args__ = (
        Index("ix_bids_rfq_total", "rfq_id", "total_amount"),  # serves "lowest bid per RFQ" and ranking
        CheckConstraint("total_amount > 0", name="ck_bid_positive_total"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rfq_id: Mapped[int] = mapped_column(ForeignKey("rfqs.id", ondelete="CASCADE"))
    carrier_name: Mapped[str] = mapped_column(String(100))

    freight_charges: Mapped[Decimal] = mapped_column(Money)
    origin_charges: Mapped[Decimal] = mapped_column(Money)
    destination_charges: Mapped[Decimal] = mapped_column(Money)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))  # denormalised so SQL can sort and aggregate on it

    transit_days: Mapped[int]
    quote_valid_until: Mapped[date]
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)

    rfq: Mapped[Rfq] = relationship(back_populates="bids")


class AuctionEvent(Base):
    """Append-only activity log: what happened, when, and why the clock moved."""

    __tablename__ = "auction_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    rfq_id: Mapped[int] = mapped_column(ForeignKey("rfqs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[EventKind] = mapped_column(_enum(EventKind))
    message: Mapped[str] = mapped_column(String(300))
    details: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
