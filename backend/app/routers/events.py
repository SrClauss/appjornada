import asyncio
import json
from typing import AsyncGenerator, Set
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/events", tags=["events"])


class EventManager:
    def __init__(self):
        self.subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    async def broadcast(self, event_type: str, data: dict) -> None:
        payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
        for q in list(self.subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass


event_manager = EventManager()


@router.get("/stream")
async def stream_events(request: Request):
    """
    Endpoint SSE (Server-Sent Events) para transmissão em tempo real de eventos para o Painel de Controle.
    Elimina o polling contínuo de 10s e economiza recursos do navegador e do servidor.
    """
    q = event_manager.subscribe()

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield "data: " + json.dumps({"type": "ping", "data": "connected"}) + "\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield "data: " + json.dumps({"type": "ping", "data": "keepalive"}) + "\n\n"
        finally:
            event_manager.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
