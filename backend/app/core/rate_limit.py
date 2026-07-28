import hashlib
import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Limit:
    requests: int
    window: int

    @classmethod
    def parse(cls, value: str) -> "Limit":
        requests, window = value.split("/", 1)
        return cls(int(requests), int(window))


class RateLimiter:
    def __init__(self) -> None:
        self._memory: dict[str, tuple[int, int]] = {}
        self._redis = None
        if settings.redis_url:
            from redis import Redis
            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)

    def check(self, bucket: str, identity: str, configured_limit: str) -> None:
        limit = Limit.parse(configured_limit)
        now = int(time.time())
        window = now // limit.window
        digest = hashlib.sha256(identity.strip().lower().encode()).hexdigest()
        key = f"ecoevent:rl:{bucket}:{digest}:{window}"
        try:
            if self._redis is not None:
                count = int(self._redis.incr(key))
                if count == 1:
                    self._redis.expire(key, limit.window + 1)
            else:
                count, old_window = self._memory.get(key, (0, window))
                count = count + 1 if old_window == window else 1
                self._memory[key] = (count, window)
        except Exception as exc:
            logger.error("rate_limiter_unavailable bucket=%s", bucket)
            if settings.app_env.lower() == "production":
                raise HTTPException(status_code=503, detail="Security service unavailable") from exc
            return
        if count > limit.requests:
            retry_after = limit.window - (now % limit.window)
            logger.warning("rate_limit_exceeded bucket=%s", bucket)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if settings.trusted_proxy_count <= 0:
        return peer
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    if len(forwarded) < settings.trusted_proxy_count:
        return peer
    return (forwarded + [peer])[-(settings.trusted_proxy_count + 1)]


def enforce(request: Request, bucket: str, identity: str, configured_limit: str) -> None:
    limiter.check(bucket, f"{client_ip(request)}:{identity}", configured_limit)
