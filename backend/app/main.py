from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import service
from .db import Base, engine, get_db
from .realtime import hub
from .schemas import BidCreate, RfqCreate, RfqDetail, RfqSummary


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # shortcut: no migrations; add Alembic once the schema has to evolve in prod
    yield


def clock() -> datetime:
    """Single source of 'now', injected so tests can time-travel through an auction."""
    return datetime.now(UTC)


Db = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(clock)]

app = FastAPI(title="British Auction RFQ", lifespan=lifespan)
api = APIRouter(prefix="/api")


@app.exception_handler(service.AuctionError)
async def auction_error(_: Request, exc: service.AuctionError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)


@api.get("/rfqs", response_model=list[RfqSummary])
def list_rfqs(db: Db, now: Now):
    return service.list_rfqs(db, now)


@api.post("/rfqs", response_model=RfqDetail, status_code=201)
def create_rfq(data: RfqCreate, db: Db, now: Now):
    return service.rfq_detail(service.create_rfq(db, data, now), now)


@api.get("/rfqs/{rfq_id}", response_model=RfqDetail)
def get_rfq(rfq_id: int, db: Db, now: Now):
    return service.rfq_detail(service.get_rfq(db, rfq_id), now)


@api.post("/rfqs/{rfq_id}/bids", response_model=RfqDetail, status_code=201)
def place_bid(rfq_id: int, data: BidCreate, db: Db, now: Now, tasks: BackgroundTasks):
    rfq = service.place_bid(db, rfq_id, data, now)
    tasks.add_task(hub.publish, rfq_id)  # runs after the response, i.e. after the commit is visible
    return service.rfq_detail(rfq, now)


@api.websocket("/rfqs/{rfq_id}/live")
async def watch_rfq(ws: WebSocket, rfq_id: int):
    async with hub.watch(rfq_id, ws):
        try:
            while True:
                await ws.receive_text()  # we only push; reading just detects the disconnect
        except WebSocketDisconnect:
            pass


app.include_router(api)

# In the Docker image the built React app is served from here, so the whole product is one container.
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        return FileResponse(STATIC_DIR / "index.html")
