from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BridgeSettings:
    jwks_url: str
    issuer: str
    audience: str | tuple[str, ...] = "authenticated"
    algorithms: tuple[str, ...] = ("ES256", "RS256")
    jwks_ttl_seconds: int = 36000
    internal_service_key: str | None = None
    internal_header_name: str = "X-Internal-Service-Key"

    def __post_init__(self) -> None:
        if not self.jwks_url:
            raise ValueError("jwks_url is required")
        if not self.issuer:
            raise ValueError("issuer is required")
        if self.jwks_ttl_seconds <= 0:
            raise ValueError("jwks_ttl_seconds must be positive")
        if not self.algorithms:
            raise ValueError("at least one JWT algorithm is required")
        if not self.internal_header_name:
            raise ValueError("internal_header_name is required")
