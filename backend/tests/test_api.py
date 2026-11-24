"""End-to-end scenarios through the HTTP API, with an injectable clock to walk through an auction."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app, clock

CLOSE = datetime(2030, 1, 1, 18, 0, tzinfo=UTC)
MIN = timedelta(minutes=1)


@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)

    def db():
        with Session() as s:
            yield s

    now = {"t": CLOSE - 30 * MIN}
    app.dependency_overrides = {get_db: db, clock: lambda: now["t"]}
    client = TestClient(app)
    client.at = lambda t: now.update(t=t)  # time travel
    yield client
    app.dependency_overrides = {}


def create(api, trigger="bid_received", forced=CLOSE + 12 * MIN, **overrides):
    body = {
        "reference_id": "RFQ-1", "name": "Mumbai to Rotterdam", "pickup_date": "2030-01-10",
        "bid_start_at": (CLOSE - 60 * MIN).isoformat(), "bid_close_at": CLOSE.isoformat(),
        "forced_close_at": forced.isoformat(), "trigger_window_minutes": 10, "extension_minutes": 5,
        "trigger_type": trigger, **overrides,
    }
    return api.post("/api/rfqs", json=body)


def bid(api, carrier, freight):
    return api.post("/api/rfqs/1/bids", json={
        "carrier_name": carrier, "freight_charges": str(freight), "origin_charges": "10",
        "destination_charges": "5", "transit_days": 20, "quote_valid_until": "2030-02-01",
    })


def test_forced_close_must_be_after_close(api):
    r = create(api, forced=CLOSE)
    assert r.status_code == 422
    assert "Forced close time must be after bid close time" in r.text


def test_duplicate_reference_is_rejected(api):
    assert create(api).status_code == 201
    assert create(api).status_code == 409


def test_bid_outside_window_does_not_extend(api):
    create(api)
    detail = bid(api, "Maersk", 1000).json()
    assert detail["bid_close_at"] == CLOSE.isoformat().replace("+00:00", "Z")
    assert detail["ranking"][0]["total_amount"] == "1015.00"


def test_bid_in_window_extends_and_extensions_cap_at_forced_close(api):
    create(api)  # forced close = close + 12 min, extension = 5 min
    for minute, price in [(2, 900), (6, 800), (10, 700)]:
        api.at(CLOSE - 5 * MIN + minute * MIN)
        assert bid(api, "Maersk", price).status_code == 201

    detail = api.get("/api/rfqs/1").json()
    assert detail["stats"]["extension_count"] == 3
    assert detail["bid_close_at"] == detail["forced_close_at"]
    assert "capped at forced close" in detail["events"][0]["message"]

    api.at(CLOSE + 12 * MIN)
    assert api.get("/api/rfqs/1").json()["status"] == "force_closed"
    assert bid(api, "MSC", 500).status_code == 409


def test_l1_trigger_ignores_bids_that_do_not_change_the_leader(api):
    create(api, trigger="l1_change")
    bid(api, "Maersk", 500)
    api.at(CLOSE - 2 * MIN)
    assert bid(api, "MSC", 900).json()["stats"]["extension_count"] == 0  # MSC lands at L2
    assert bid(api, "MSC", 400).json()["stats"]["extension_count"] == 1  # MSC takes L1


def test_supplier_must_beat_own_previous_bid(api):
    create(api)
    bid(api, "Maersk", 500)
    r = bid(api, "Maersk", 500)
    assert r.status_code == 409
    assert "lower than your previous best" in r.json()["detail"]


def test_listing_shows_lowest_bid_and_status(api):
    create(api)
    bid(api, "Maersk", 500)
    bid(api, "MSC", 300)
    [row] = api.get("/api/rfqs").json()
    assert (row["lowest_bid"], row["bid_count"], row["status"]) == ("315.00", 2, "active")
