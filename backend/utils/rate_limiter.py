"""
rate_limiter.py — Per-provider concurrency limits and exponential backoff.
Used by all agents that make external API calls.

Async version — orchestrator.py is fully async so all semaphores and sleeps
must be async-compatible. Threading semaphores and time.sleep would block the
event loop and kill parallelism.
"""

import asyncio
import logging
import random
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

# ── Provider concurrency limits ───────────────────────────────────────────────
_CONCURRENCY = {
    "gemini_flash": 1,   # Gemini 2.0 Flash — free tier, sequential to avoid TPM floods
    "gemini_pro":   1,   # Gemini 2.5 Pro   — free tier, strict 5 RPM sequential
    "groq":         8,   # Groq              — high throughput, generous limit
    "cerebras":     4,   # Cerebras          — fast inference, numerical verifier
}

# asyncio.Semaphore must be created inside a running event loop.
# _get_semaphore() lazily creates them on first use (safe for FastAPI + uvicorn).
_SEMAPHORES: dict[str, asyncio.Semaphore] = {}
_sem_lock = Lock()


def _get_semaphore(provider: str) -> asyncio.Semaphore:
    """Return (creating if needed) the asyncio.Semaphore for a provider."""
    if provider not in _SEMAPHORES:
        with _sem_lock:
            if provider not in _SEMAPHORES:  # double-check after acquiring lock
                limit = _CONCURRENCY.get(provider, 1)
                _SEMAPHORES[provider] = asyncio.Semaphore(limit)
    return _SEMAPHORES[provider]


class RateLimiter:
    """
    Named semaphore accessors. Passed into orchestrator and agents.

    Usage:
        async with rate_limiter.flash:
            result = await with_backoff(my_coro, provider="gemini_flash")
    """

    @property
    def flash(self) -> asyncio.Semaphore:
        return _get_semaphore("gemini_flash")

    @property
    def pro(self) -> asyncio.Semaphore:
        return _get_semaphore("gemini_pro")

    @property
    def groq(self) -> asyncio.Semaphore:
        return _get_semaphore("groq")

    @property
    def cerebras(self) -> asyncio.Semaphore:
        return _get_semaphore("cerebras")


# Singleton used across the codebase
rate_limiter = RateLimiter()

# ── Backoff config ────────────────────────────────────────────────────────────
_BASE_DELAY_SECONDS = 2.0
_MAX_DELAY_SECONDS  = 60.0
_MAX_RETRIES        = 5

# ── Request tracking ──────────────────────────────────────────────────────────
_stats_lock = Lock()
_request_counts: dict[str, int] = defaultdict(int)
_failure_counts: dict[str, int] = defaultdict(int)


# ── Core backoff function ─────────────────────────────────────────────────────

async def with_backoff(coro_fn, *args, provider: str = "gemini_flash",
                       agent: str = "unknown", **kwargs):
    """
    Await coro_fn(*args, **kwargs) with exponential backoff on rate-limit errors.
    The provider semaphore must be acquired by the caller (via `async with rate_limiter.flash`).
    This function handles retry logic only — not concurrency gating.

    Args:
        coro_fn : Async callable to execute.
        *args   : Forwarded to coro_fn.
        provider: Used for stats tracking only (semaphore held by caller).
        agent   : Used in log messages.
        **kwargs: Forwarded to coro_fn.

    Returns:
        Return value of coro_fn on success.

    Raises:
        Last exception if all retries are exhausted.
    """
    last_exc = None
    delay = _BASE_DELAY_SECONDS

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            result = await coro_fn(*args, **kwargs)
            with _stats_lock:
                _request_counts[provider] += 1
            return result

        except Exception as exc:  # noqa: BLE001
            exc_str = str(exc).lower()
            is_rate_limit = (
                "429"                  in str(exc)
                or "rate limit"        in exc_str
                or "too many requests" in exc_str
                or "ratelimit"         in exc_str
                or "quota"             in exc_str
            )

            if is_rate_limit and attempt < _MAX_RETRIES:
                if "quota" in exc_str or "exhausted" in exc_str or "tokens" in exc_str:
                    # Input token quota exceeded on Free Tier: sleep 60s to completely reset it.
                    sleep_for = 60.0
                else:
                    jitter = random.uniform(0, delay * 0.3)
                    sleep_for = min(delay + jitter, _MAX_DELAY_SECONDS)
                logger.warning(
                    "Rate limit hit | provider=%s | agent=%s | attempt=%d/%d | retrying in %.1fs",
                    provider, agent, attempt, _MAX_RETRIES, sleep_for,
                )
                await asyncio.sleep(sleep_for)
                delay = min(delay * 2, _MAX_DELAY_SECONDS)
                last_exc = exc
            else:
                with _stats_lock:
                    _failure_counts[provider] += 1
                raise

    raise last_exc  # pragma: no cover


def with_backoff_sync(fn, *args, provider: str = "gemini_flash",
                      agent: str = "unknown", **kwargs):
    """
    Call fn(*args, **kwargs) with exponential backoff on rate-limit errors (synchronous).
    This runs synchronously inside thread workers and uses time.sleep() which blocks
    only the worker thread, keeping the orchestrator event loop active.
    """
    import time
    last_exc = None
    delay = _BASE_DELAY_SECONDS

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            result = fn(*args, **kwargs)
            with _stats_lock:
                _request_counts[provider] += 1
            return result

        except Exception as exc:
            exc_str = str(exc).lower()
            is_rate_limit = (
                "429"                  in str(exc)
                or "rate limit"        in exc_str
                or "too many requests" in exc_str
                or "ratelimit"         in exc_str
                or "quota"             in exc_str
                or "exhausted"         in exc_str
            )

            if is_rate_limit and attempt < _MAX_RETRIES:
                if "quota" in exc_str or "exhausted" in exc_str or "tokens" in exc_str:
                    # Input token quota exceeded on Free Tier: sleep 60s to completely reset it.
                    sleep_for = 60.0
                else:
                    jitter = random.uniform(0, delay * 0.3)
                    sleep_for = min(delay + jitter, _MAX_DELAY_SECONDS)
                logger.warning(
                    "Rate limit hit | provider=%s | agent=%s | attempt=%d/%d | retrying in %.1fs (sync)",
                    provider, agent, attempt, _MAX_RETRIES, sleep_for,
                )
                time.sleep(sleep_for)
                delay = min(delay * 2, _MAX_DELAY_SECONDS)
                last_exc = exc
            else:
                with _stats_lock:
                    _failure_counts[provider] += 1
                raise

    raise last_exc




# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Return current request and failure counts per provider."""
    with _stats_lock:
        return {
            "requests": dict(_request_counts),
            "failures": dict(_failure_counts),
        }


def patch_gemini_sdk():
    """
    Globally monkey-patch google.generativeai.GenerativeModel
    to redirect gemini-2.0-flash to gemini-2.5-flash and
    transparently route all Gemini requests through with_backoff_sync.
    This guarantees robust exponential backoff and avoids free-tier daily quota depletion.
    """
    try:
        import google.generativeai as genai
        
        # 1. Patch __init__ to dynamically redirect model name
        original_init = genai.GenerativeModel.__init__
        if not getattr(original_init, "_is_patched", False):
            def patched_init(self, model_name="gemini-1.5-flash", *args, **kwargs):
                if "gemini-2.0-flash" in model_name or "gemini-2.5-flash" in model_name:
                    target_model = "gemini-flash-lite-latest"
                    logger.info("Redirecting GenerativeModel: %s -> %s", model_name, target_model)
                    model_name = target_model
                original_init(self, model_name, *args, **kwargs)
            patched_init._is_patched = True
            genai.GenerativeModel.__init__ = patched_init
            logger.info("Successfully patched GenerativeModel.__init__ for 2.0/2.5 -> gemini-flash-lite-latest redirection.")

        # 2. Patch generate_content for synchronous backoff
        original_gen = genai.GenerativeModel.generate_content
        if not getattr(original_gen, "_is_patched", False):
            def patched_generate_content(self, *args, **kwargs):
                model_name = getattr(self, "model_name", "gemini-2.5-flash")
                model_clean = model_name.split("/")[-1]
                provider = "gemini_pro" if "pro" in model_clean else "gemini_flash"
                
                logger.debug("Routing patched generate_content call for %s", model_name)
                return with_backoff_sync(
                    original_gen,
                    self,
                    *args,
                    provider=provider,
                    agent=model_clean,
                    **kwargs
                )
            patched_generate_content._is_patched = True
            genai.GenerativeModel.generate_content = patched_generate_content
            logger.info("Successfully patched GenerativeModel.generate_content with backoff.")

    except Exception as exc:
        logger.error("Failed to monkey-patch Google GenAI SDK: %s", exc)