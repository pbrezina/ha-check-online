"""Helpers for the Check Online integration."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import socket
import time

from homeassistant.core import HomeAssistant

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

        ip = result[0][4][0]
        self._cache[host] = DnsCacheEntry(
            ip_address=ip,
            expires_at=time.monotonic() + self._ttl,
        )
        return ip
