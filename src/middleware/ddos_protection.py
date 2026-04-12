import hashlib
import logging
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.util import get_remote_address

logger = logging.getLogger("portfolio.security")

# Sliding window rate limiting with fingerprinting
_request_history: dict[str, list[float]] = defaultdict(list)
_fingerprint_history: dict[str, list[float]] = defaultdict(list)

# Threshold values
MAX_REQUESTS_PER_MINUTE = 10  # Hard limit
MAX_REQUESTS_PER_HOUR = 100  # Hard limit
SUSPICIOUS_PATTERN_THRESHOLD = 5  # Number of blocked attempts before flag
REQUEST_TIMEOUT_SECONDS = 300  # Clean up old entries after 5 minutes


def _get_request_fingerprint(request: Request, body: bytes) -> str:
    """Generate a fingerprint based on IP, User-Agent, and request pattern"""
    ip = get_remote_address(request)
    user_agent = request.headers.get("user-agent", "unknown")
    content_hash = hashlib.md5(body[:100]).hexdigest()  # Hash first 100 bytes

    fingerprint_str = f"{ip}:{user_agent}:{content_hash}"
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]


def _clean_old_requests(window_key: str, cutoff_time: float) -> None:
    """Remove requests older than cutoff_time"""
    if window_key in _request_history:
        _request_history[window_key] = [
            t for t in _request_history[window_key] if t > cutoff_time
        ]
        if not _request_history[window_key]:
            del _request_history[window_key]


def _check_sliding_window(window_key: str, current_time: float, max_requests: int, window_seconds: int) -> bool:
    """Check if request exceeds sliding window limit"""
    cutoff_time = current_time - window_seconds
    _clean_old_requests(window_key, cutoff_time)

    if len(_request_history[window_key]) >= max_requests:
        return False

    _request_history[window_key].append(current_time)
    return True


async def ddos_protection_middleware(request: Request, call_next):
    """
    Advanced DDoS protection with:
    - Sliding window rate limiting
    - Request fingerprinting
    - Suspicious pattern detection
    - Payload size validation
    """
    current_time = time.time()
    ip = get_remote_address(request)

    # 1. Check Content-Length header
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 50_000:  # 50KB hard limit
                logger.warning(f"DDOS_ATTEMPT ip={ip} reason=oversized_payload size={content_length}")
                return JSONResponse(status_code=413, content={"detail": "Payload too large"})
        except ValueError:
            pass

    # 2. Read body for fingerprinting
    body = await request.body()
    fingerprint = _get_request_fingerprint(request, body)

    # 3. IP-based sliding window (hard limits)
    if not _check_sliding_window(f"ip:{ip}", current_time, MAX_REQUESTS_PER_MINUTE, 60):
        logger.warning(f"DDOS_ATTEMPT ip={ip} reason=rate_limit_1min")
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})

    if not _check_sliding_window(f"ip:{ip}", current_time, MAX_REQUESTS_PER_HOUR, 3600):
        logger.warning(f"DDOS_ATTEMPT ip={ip} reason=rate_limit_1hour")
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})

    # 4. Fingerprint-based detection (catch distributed attacks)
    if not _check_sliding_window(f"fp:{fingerprint}", current_time, MAX_REQUESTS_PER_MINUTE * 2, 60):
        logger.warning(f"SUSPICIOUS_FINGERPRINT fingerprint={fingerprint} ip={ip}")
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})

    # 5. Detect rapid repeated failures (credential stuffing / brute force pattern)
    suspicious_key = f"suspicious:{ip}"
    cutoff_time = current_time - 300  # 5 minute window
    _clean_old_requests(suspicious_key, cutoff_time)

    if len(_request_history.get(suspicious_key, [])) > SUSPICIOUS_PATTERN_THRESHOLD:
        logger.critical(f"SUSPICIOUS_PATTERN ip={ip} attempts={len(_request_history[suspicious_key])}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Access denied due to suspicious activity"}
        )

    # 6. Check for User-Agent spoofing or missing headers
    user_agent = request.headers.get("user-agent", "")
    if not user_agent:
        logger.warning(f"DDOS_ATTEMPT ip={ip} reason=missing_user_agent")
        return JSONResponse(status_code=400, content={"detail": "Invalid request"})

    # Continue to next middleware
    response = await call_next(request)

    # 7. Track failed responses (4xx, 5xx)
    if response.status_code >= 400:
        _request_history[suspicious_key].append(current_time)

    return response
