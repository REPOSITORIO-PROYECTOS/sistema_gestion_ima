"""Rate limiting en memoria para el endpoint de login (anti fuerza bruta)."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple

_lock = threading.Lock()

_WINDOW_IP_SECONDS = int(os.getenv("LOGIN_RATE_WINDOW_IP_SECONDS", "600"))
_MAX_ATTEMPTS_IP = int(os.getenv("LOGIN_RATE_MAX_ATTEMPTS_IP", "20"))
_LOCKOUT_IP_SECONDS = int(os.getenv("LOGIN_RATE_LOCKOUT_IP_SECONDS", "900"))

_WINDOW_USER_SECONDS = int(os.getenv("LOGIN_RATE_WINDOW_USER_SECONDS", "900"))
_MAX_ATTEMPTS_USER = int(os.getenv("LOGIN_RATE_MAX_ATTEMPTS_USER", "8"))
_LOCKOUT_USER_SECONDS = int(os.getenv("LOGIN_RATE_LOCKOUT_USER_SECONDS", "600"))


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


def _client_key(ip: str, username: str) -> Tuple[str, str]:
    return ip.strip() or "unknown", (username or "").strip().lower()


def _purge_old(entries: Deque[float], window_seconds: int, now: float) -> None:
    cutoff = now - window_seconds
    while entries and entries[0] < cutoff:
        entries.popleft()


def _is_locked(lock_until: Dict[str, float], key: str, now: float) -> int:
    until = lock_until.get(key, 0.0)
    if until <= now:
        lock_until.pop(key, None)
        return 0
    return max(1, int(until - now))


_ip_attempts: Dict[str, Deque[float]] = defaultdict(deque)
_user_attempts: Dict[str, Deque[float]] = defaultdict(deque)
_ip_lock_until: Dict[str, float] = {}
_user_lock_until: Dict[str, float] = {}


def check_login_allowed(ip: str, username: str) -> RateLimitResult:
    now = time.monotonic()
    ip_key, user_key = _client_key(ip, username)
    composite_key = f"{ip_key}:{user_key}"

    with _lock:
        ip_retry = _is_locked(_ip_lock_until, ip_key, now)
        if ip_retry:
            return RateLimitResult(allowed=False, retry_after_seconds=ip_retry)

        user_retry = _is_locked(_user_lock_until, composite_key, now)
        if user_retry:
            return RateLimitResult(allowed=False, retry_after_seconds=user_retry)

        ip_entries = _ip_attempts[ip_key]
        _purge_old(ip_entries, _WINDOW_IP_SECONDS, now)
        if len(ip_entries) >= _MAX_ATTEMPTS_IP:
            _ip_lock_until[ip_key] = now + _LOCKOUT_IP_SECONDS
            return RateLimitResult(allowed=False, retry_after_seconds=_LOCKOUT_IP_SECONDS)

        user_entries = _user_attempts[composite_key]
        _purge_old(user_entries, _WINDOW_USER_SECONDS, now)
        if len(user_entries) >= _MAX_ATTEMPTS_USER:
            _user_lock_until[composite_key] = now + _LOCKOUT_USER_SECONDS
            return RateLimitResult(allowed=False, retry_after_seconds=_LOCKOUT_USER_SECONDS)

    return RateLimitResult(allowed=True)


def register_login_failure(ip: str, username: str) -> None:
    now = time.monotonic()
    ip_key, user_key = _client_key(ip, username)
    composite_key = f"{ip_key}:{user_key}"

    with _lock:
        _ip_attempts[ip_key].append(now)
        _user_attempts[composite_key].append(now)


def register_login_success(ip: str, username: str) -> None:
    ip_key, user_key = _client_key(ip, username)
    composite_key = f"{ip_key}:{user_key}"

    with _lock:
        _ip_attempts.pop(ip_key, None)
        _user_attempts.pop(composite_key, None)
        _ip_lock_until.pop(ip_key, None)
        _user_lock_until.pop(composite_key, None)
