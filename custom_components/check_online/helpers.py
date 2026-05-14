"""Helpers for the Check Online integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import enum
import ipaddress
import logging
import re
import socket
import time

from homeassistant.core import HomeAssistant
from icmplib import SocketPermissionError as IcmpSocketPermissionError
from icmplib import async_ping as icmplib_async_ping

from .const import DEFAULT_DNS_TTL


@dataclass
class DnsCacheEntry:
    """A cached DNS resolution result."""

    ip_address: str
    expires_at: float


class DnsResolver:
    """Resolve hostnames to IP addresses with TTL-based caching."""

    def __init__(self, hass: HomeAssistant, ttl: int = DEFAULT_DNS_TTL) -> None:
        self._hass = hass
        self._ttl = ttl
        self._cache: dict[str, DnsCacheEntry] = {}

    def _is_ip_address(self, host: str) -> bool:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return False
        return True

    async def resolve(self, host: str) -> str | None:
        """Resolve a hostname to an IP address.

        Returns the IP directly if host is already an IP address.
        Returns None if DNS resolution fails.
        """
        if self._is_ip_address(host):
            return host

        cached = self._cache.get(host)
        if cached is not None and cached.expires_at > time.monotonic():
            return cached.ip_address

        try:
            result = await self._hass.async_add_executor_job(
                socket.getaddrinfo, host, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
        except socket.gaierror:
            self._cache.pop(host, None)
            return None

        if not result:
            self._cache.pop(host, None)
            return None

        ip: str = str(result[0][4][0])
        self._cache[host] = DnsCacheEntry(
            ip_address=ip,
            expires_at=time.monotonic() + self._ttl,
        )
        return ip


_LOGGER = logging.getLogger(__name__)


class PingMode(enum.Enum):
    """How to send ICMP pings."""

    PRIVILEGED = "privileged"
    UNPRIVILEGED = "unprivileged"
    SUBPROCESS = "subprocess"


@dataclass(frozen=True)
class PingResult:
    """Result of a single ping attempt."""

    is_alive: bool
    rtt: float | None  # milliseconds


async def detect_ping_mode() -> PingMode:
    """Detect the best available ping method.

    Tries privileged icmplib, then unprivileged, then falls back to subprocess.
    """
    try:
        await icmplib_async_ping("127.0.0.1", count=0, timeout=0, privileged=True)
        return PingMode.PRIVILEGED
    except IcmpSocketPermissionError:
        pass

    try:
        await icmplib_async_ping("127.0.0.1", count=0, timeout=0, privileged=False)
        return PingMode.UNPRIVILEGED
    except IcmpSocketPermissionError:
        pass

    return PingMode.SUBPROCESS


async def ping_icmplib(ip: str, timeout_ms: int, *, privileged: bool) -> PingResult:
    """Ping a host using icmplib."""
    try:
        result = await icmplib_async_ping(
            ip,
            count=1,
            timeout=timeout_ms / 1000.0,
            privileged=privileged,
        )
        return PingResult(
            is_alive=result.is_alive,
            rtt=result.avg_rtt if result.is_alive else None,
        )
    except Exception:
        _LOGGER.debug("icmplib ping failed for %s", ip, exc_info=True)
        return PingResult(is_alive=False, rtt=None)


async def ping_subprocess(ip: str, timeout_ms: int) -> PingResult:
    """Ping a host using the system ping command."""
    timeout_sec = max(1, round(timeout_ms / 1000))
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping",
            "-c",
            "1",
            "-W",
            str(timeout_sec),
            ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec + 5)
        if proc.returncode == 0:
            match = re.search(r"time[=<](\d+\.?\d*)", stdout.decode())
            rtt = float(match.group(1)) if match else None
            return PingResult(is_alive=True, rtt=rtt)
    except Exception:
        _LOGGER.debug("Subprocess ping failed for %s", ip, exc_info=True)

    return PingResult(is_alive=False, rtt=None)


class PingHelper:
    """Ping hosts using the detected best method."""

    def __init__(self, mode: PingMode, timeout_ms: int) -> None:
        self._mode = mode
        self._timeout_ms = timeout_ms

    async def ping(self, ip: str) -> PingResult:
        """Ping a single IP address."""
        if self._mode == PingMode.SUBPROCESS:
            return await ping_subprocess(ip, self._timeout_ms)
        return await ping_icmplib(
            ip,
            self._timeout_ms,
            privileged=(self._mode == PingMode.PRIVILEGED),
        )

    async def ping_all(self, ips: list[str]) -> dict[str, PingResult]:
        """Ping multiple IPs concurrently. Returns results keyed by IP."""
        results = await asyncio.gather(*(self.ping(ip) for ip in ips))
        return dict(zip(ips, results, strict=True))
