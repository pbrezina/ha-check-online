"""Tests for check_online helpers."""

from __future__ import annotations

import socket
import time
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.check_online.helpers import DnsResolver


class TestDnsResolver:
    """Tests for DNS resolver with TTL cache."""

    async def test_resolve_ip_address_passthrough(self) -> None:
        """IP addresses should be returned as-is without DNS lookup."""
        hass = MagicMock()
        resolver = DnsResolver(hass)

        result = await resolver.resolve("8.8.8.8")

        assert result == "8.8.8.8"
        hass.async_add_executor_job.assert_not_called()

    async def test_resolve_ipv6_address_passthrough(self) -> None:
        """IPv6 addresses should be returned as-is without DNS lookup."""
        hass = MagicMock()
        resolver = DnsResolver(hass)

        result = await resolver.resolve("2001:4860:4860::8888")

        assert result == "2001:4860:4860::8888"
        hass.async_add_executor_job.assert_not_called()

    async def test_resolve_hostname_success(self) -> None:
        """Hostname should be resolved via getaddrinfo."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]
        )
        resolver = DnsResolver(hass)

        result = await resolver.resolve("example.com")

        assert result == "93.184.216.34"

    async def test_resolve_hostname_cached(self) -> None:
        """Second call within TTL should use cache, not call getaddrinfo."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]
        )
        resolver = DnsResolver(hass, ttl=3600)

        await resolver.resolve("example.com")
        await resolver.resolve("example.com")

        assert hass.async_add_executor_job.call_count == 1

    async def test_resolve_hostname_cache_expired(self) -> None:
        """After TTL expires, should resolve again."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]
        )
        resolver = DnsResolver(hass, ttl=1)

        await resolver.resolve("example.com")

        with patch("custom_components.check_online.helpers.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2
            await resolver.resolve("example.com")

        assert hass.async_add_executor_job.call_count == 2

    async def test_resolve_hostname_failure_returns_none(self) -> None:
        """DNS failure should return None."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(side_effect=socket.gaierror)
        resolver = DnsResolver(hass)

        result = await resolver.resolve("nonexistent.invalid")

        assert result is None

    async def test_resolve_hostname_failure_clears_cache(self) -> None:
        """DNS failure should clear any previously cached entry."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]
        )
        resolver = DnsResolver(hass, ttl=1)

        result = await resolver.resolve("example.com")
        assert result == "93.184.216.34"

        with patch("custom_components.check_online.helpers.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2
            hass.async_add_executor_job = AsyncMock(side_effect=socket.gaierror)
            result = await resolver.resolve("example.com")

        assert result is None

    async def test_resolve_empty_result_returns_none(self) -> None:
        """Empty getaddrinfo result should return None."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(return_value=[])
        resolver = DnsResolver(hass)

        result = await resolver.resolve("example.com")

        assert result is None
