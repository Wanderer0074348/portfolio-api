import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.agents import chat_agent
from src.agents.topic_guard import is_on_topic
from src.models.chat import MAX_HISTORY_TURNS, ChatRequest, ChatResponse

logger = logging.getLogger("portfolio.security")

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

OFF_TOPIC_REPLY = "ACCESS_DENIED: Query out of scope. I only answer questions about Tanay Matta."


@router.get("/health")
@limiter.limit("10/minute")
async def health(request: Request):
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("3/5minutes;36/hour")
async def chat(req: ChatRequest, request: Request):
    from slowapi.util import get_remote_address
    ip = get_remote_address(request)

    history = [
        {"role": m.role, "content": m.content}
        for m in req.history[-MAX_HISTORY_TURNS:]
    ]

    if not is_on_topic(req.message, history):
        logger.warning(f"OFF_TOPIC ip={ip} message={req.message[:80]}")
        return ChatResponse(response=OFF_TOPIC_REPLY)

    try:
        reply = chat_agent.run(req.message, history)
    except Exception as e:
        logger.error(f"UPSTREAM ERROR ip={ip} error={e}")
        raise HTTPException(status_code=502, detail="Upstream error.")

    return ChatResponse(response=reply)
