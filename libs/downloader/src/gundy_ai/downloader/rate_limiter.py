"""Rate limiting for downloads."""

from __future__ import annotations

import asyncio

import structlog
from aiolimiter import AsyncLimiter

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Rate limiter for download operations."""

    def __init__(
        self,
        max_requests_per_second: float = 1.0,
        max_concurrent_downloads: int = 3,
        burst_size: int = 5,
    ):
        """Initialize rate limiter.

        Args:
            max_requests_per_second: Maximum requests per second
            max_concurrent_downloads: Maximum concurrent downloads
            burst_size: Burst allowance for rate limiting
        """
        self.max_requests_per_second = max_requests_per_second
        self.max_concurrent_downloads = max_concurrent_downloads
        self.burst_size = burst_size

        # Create rate limiter
        self.limiter = AsyncLimiter(max_rate=max_requests_per_second, time_period=1.0)

        # Semaphore for concurrent downloads
        self.semaphore = asyncio.Semaphore(max_concurrent_downloads)

        # Per-domain limiters
        self.domain_limiters: dict[str, AsyncLimiter] = {}

        self.logger = logger.bind(rate_limiter=True)

        self.logger.info(
            "rate_limiter.initialized",
            max_requests_per_second=max_requests_per_second,
            max_concurrent_downloads=max_concurrent_downloads,
            burst_size=burst_size,
        )

    async def acquire(self, domain: str | None = None) -> None:
        """Acquire rate limit permission.

        Args:
            domain: Optional domain-specific limiting
        """
        # Acquire general rate limit
        await self.limiter.acquire()

        # Acquire domain-specific rate limit if provided
        if domain:
            await self._get_domain_limiter(domain).acquire()

        # Acquire concurrent download semaphore
        await self.semaphore.acquire()

        self.logger.debug(
            "rate_limiter.acquired",
            domain=domain,
            concurrent_downloads=self.max_concurrent_downloads - self.semaphore._value,
        )

    def release(self) -> None:
        """Release concurrent download semaphore."""
        self.semaphore.release()

        self.logger.debug(
            "rate_limiter.released",
            concurrent_downloads=self.max_concurrent_downloads - self.semaphore._value,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.release()

    def _get_domain_limiter(self, domain: str) -> AsyncLimiter:
        """Get or create domain-specific limiter."""
        if domain not in self.domain_limiters:
            # Use more restrictive limits for domain-specific limiting
            domain_rate = min(self.max_requests_per_second, 0.5)
            self.domain_limiters[domain] = AsyncLimiter(
                max_rate=domain_rate,
                time_period=1.0,
            )

            self.logger.info(
                "rate_limiter.domain_created",
                domain=domain,
                rate=domain_rate,
            )

        return self.domain_limiters[domain]

    def set_domain_rate(self, domain: str, rate: float) -> None:
        """Set custom rate for a specific domain."""
        self.domain_limiters[domain] = AsyncLimiter(max_rate=rate, time_period=1.0)

        self.logger.info("rate_limiter.domain_rate_set", domain=domain, rate=rate)

    def get_stats(self) -> dict[str, any]:
        """Get current rate limiter statistics."""
        return {
            "max_requests_per_second": self.max_requests_per_second,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "current_concurrent_downloads": self.max_concurrent_downloads
            - self.semaphore._value,
            "domain_limiters_count": len(self.domain_limiters),
            "domains": list(self.domain_limiters.keys()),
        }
