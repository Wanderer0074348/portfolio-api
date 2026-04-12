import logging
import tomllib
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.controllers.chat import router as chat_router
from src.middleware.body_size import limit_body_size
from src.middleware.ddos_protection import ddos_protection_middleware

logger = logging.getLogger("portfolio.security")

_root = Path(__file__).parent.parent.parent

with open(_root / "config.toml", "rb") as _f:
    _config = tomllib.load(_f)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    ip = get_remote_address(request)
    logger.warning(f"RATE_LIMITED ip={ip} path={request.url.path} limit={exc.detail}")
    return JSONResponse(status_code=429, content={"detail": "Too many requests."})


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    limiter = Limiter(key_func=get_remote_address, default_limits=["60/hour"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_config["server"]["cors_origins"],
        allow_credentials=False,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

    app.middleware("http")(ddos_protection_middleware)
    app.middleware("http")(limit_body_size)
    app.include_router(chat_router)

    return app
