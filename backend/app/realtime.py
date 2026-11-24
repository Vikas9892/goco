from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import WebSocket


class AuctionHub:
    """Fan-out of 'auction changed' pings to browsers watching an RFQ. Clients refetch on ping,
    so the REST API stays the single source of truth and a missed message can't desync anyone.

    shortcut: in-process only, correct for a single API worker; move to Redis pub/sub before scaling out.
    """

    def __init__(self) -> None:
        self._watchers: defaultdict[int, set[WebSocket]] = defaultdict(set)

    @asynccontextmanager
    async def watch(self, rfq_id: int, ws: WebSocket):
        await ws.accept()
        self._watchers[rfq_id].add(ws)
        try:
            yield
        finally:
            self._watchers[rfq_id].discard(ws)

    async def publish(self, rfq_id: int) -> None:
        for ws in list(self._watchers[rfq_id]):
            try:
                await ws.send_json({"type": "auction_updated", "rfq_id": rfq_id})
            except Exception:  # client vanished mid-send; its own handler will clean up
                self._watchers[rfq_id].discard(ws)


hub = AuctionHub()
