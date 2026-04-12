import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.util import get_remote_address

logger = logging.getLogger("portfolio.security")

MAX_REQUEST_BYTES = 20_480


async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BYTES:
        ip = get_remote_address(request)
        logger.warning(f"BODY_TOO_LARGE ip={ip} path={request.url.path} size={content_length}")
        return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    body = await request.body()
    if len(body) > MAX_REQUEST_BYTES:
        ip = get_remote_address(request)
        logger.warning(f"BODY_TOO_LARGE ip={ip} path={request.url.path} size={len(body)}")
        return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    return await call_next(request)
