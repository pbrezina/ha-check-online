"""Tests for check_online helpers."""

from __future__ import annotations

import socket
import time
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.check_online.helpers import (
    DnsResolver,
    PingHelper,
    PingMode,
    PingResult,
    detect_ping_mode,
    ping_icmplib,
    ping_subprocess,
)


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


class TestPingResult:
    """Tests for PingResult dataclass."""

    def test_alive_with_rtt(self) -> None:
        result = PingResult(is_alive=True, rtt=12.3)
        assert result.is_alive is True
        assert result.rtt == 12.3

    def test_dead_with_no_rtt(self) -> None:
        result = PingResult(is_alive=False, rtt=None)
        assert result.is_alive is False
        assert result.rtt is None


class TestDetectPingMode:
    """Tests for privilege detection."""

    async def test_privileged_mode(self) -> None:
        """When privileged ping works, return PRIVILEGED."""
        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
        ):
            mode = await detect_ping_mode()
            assert mode == PingMode.PRIVILEGED

    async def test_unprivileged_mode(self) -> None:
        """When privileged fails but unprivileged works, return UNPRIVILEGED."""
        from icmplib import SocketPermissionError

        async def mock_ping(*args: object, **kwargs: object) -> None:
            if kwargs.get("privileged", True):
                raise SocketPermissionError(privileged=True)

        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            side_effect=mock_ping,
        ):
            mode = await detect_ping_mode()
            assert mode == PingMode.UNPRIVILEGED

    async def test_subprocess_fallback(self) -> None:
        """When both privileged and unprivileged fail, return SUBPROCESS."""
        from icmplib import SocketPermissionError

        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
            side_effect=SocketPermissionError(privileged=True),
        ):
            mode = await detect_ping_mode()
            assert mode == PingMode.SUBPROCESS


class TestPingIcmplib:
    """Tests for icmplib-based ping."""

    async def test_success(self) -> None:
        mock_host = MagicMock()
        mock_host.is_alive = True
        mock_host.avg_rtt = 12.3

        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
            return_value=mock_host,
        ):
            result = await ping_icmplib("8.8.8.8", 500, privileged=False)

        assert result.is_alive is True
        assert result.rtt == 12.3

    async def test_failure(self) -> None:
        mock_host = MagicMock()
        mock_host.is_alive = False

        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
            return_value=mock_host,
        ):
            result = await ping_icmplib("192.168.1.1", 500, privileged=False)

        assert result.is_alive is False
        assert result.rtt is None

    async def test_exception_returns_dead(self) -> None:
        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
            side_effect=Exception("socket error"),
        ):
            result = await ping_icmplib("8.8.8.8", 500, privileged=False)

        assert result.is_alive is False
        assert result.rtt is None


class TestPingSubprocess:
    """Tests for subprocess-based ping."""

    async def test_success(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (
            b"64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=12.3 ms\n",
            b"",
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ping_subprocess("8.8.8.8", 500)

        assert result.is_alive is True
        assert result.rtt == 12.3

    async def test_failure(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ping_subprocess("192.168.1.1", 500)

        assert result.is_alive is False
        assert result.rtt is None

    async def test_exception_returns_dead(self) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=OSError("ping not found"),
        ):
            result = await ping_subprocess("8.8.8.8", 500)

        assert result.is_alive is False
        assert result.rtt is None


class TestPingHelper:
    """Tests for PingHelper orchestration."""

    async def test_ping_uses_icmplib_privileged(self) -> None:
        helper = PingHelper(PingMode.PRIVILEGED, timeout_ms=500)

        with patch(
            "custom_components.check_online.helpers.ping_icmplib",
            new_callable=AsyncMock,
            return_value=PingResult(is_alive=True, rtt=10.0),
        ) as mock:
            result = await helper.ping("8.8.8.8")

        assert result.is_alive is True
        mock.assert_called_once_with("8.8.8.8", 500, privileged=True)

    async def test_ping_uses_icmplib_unprivileged(self) -> None:
        helper = PingHelper(PingMode.UNPRIVILEGED, timeout_ms=500)

        with patch(
            "custom_components.check_online.helpers.ping_icmplib",
            new_callable=AsyncMock,
            return_value=PingResult(is_alive=True, rtt=10.0),
        ) as mock:
            result = await helper.ping("8.8.8.8")

        assert result.is_alive is True
        mock.assert_called_once_with("8.8.8.8", 500, privileged=False)

    async def test_ping_uses_subprocess(self) -> None:
        helper = PingHelper(PingMode.SUBPROCESS, timeout_ms=500)

        with patch(
            "custom_components.check_online.helpers.ping_subprocess",
            new_callable=AsyncMock,
            return_value=PingResult(is_alive=True, rtt=10.0),
        ) as mock:
            result = await helper.ping("8.8.8.8")

        assert result.is_alive is True
        mock.assert_called_once_with("8.8.8.8", 500)

    async def test_ping_all_concurrent(self) -> None:
        helper = PingHelper(PingMode.UNPRIVILEGED, timeout_ms=500)

        call_order: list[str] = []

        async def mock_ping_icmplib(ip: str, timeout_ms: int, privileged: bool) -> PingResult:
            call_order.append(ip)
            return PingResult(is_alive=True, rtt=10.0)

        with patch(
            "custom_components.check_online.helpers.ping_icmplib",
            side_effect=mock_ping_icmplib,
        ):
            results = await helper.ping_all(["8.8.8.8", "1.1.1.1", "9.9.9.9"])

        assert len(results) == 3
        assert all(r.is_alive for r in results.values())
        assert set(results.keys()) == {"8.8.8.8", "1.1.1.1", "9.9.9.9"}
