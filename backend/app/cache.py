"""Tiny cache: Redis when VELDORA_REDIS_URL is set, otherwise an in-process dict with TTL."""
import json, time
from .config import settings

_mem: dict[str, tuple[float, str]] = {}
_redis = None
if settings.redis_url:
    try:
        import redis
        _redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        _redis.ping()
    except Exception:  # fall back silently; cache is an optimisation only
        _redis = None


def get(key: str):
    if _redis:
        v = _redis.get(key)
        return json.loads(v) if v else None
    hit = _mem.get(key)
    if hit and hit[0] > time.time():
        return json.loads(hit[1])
    _mem.pop(key, None)
    return None


def set(key: str, value, ttl: int = 300):
    raw = json.dumps(value, default=str)
    if _redis:
        _redis.setex(key, ttl, raw)
    else:
        _mem[key] = (time.time() + ttl, raw)
