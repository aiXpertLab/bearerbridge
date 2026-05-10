from __future__ import annotations

import time
from typing import Any

import httpx
from jose import jwk as jose_jwk
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

from bearerbridge.config import BridgeSettings
from bearerbridge.errors import TokenValidationError


class JWKSVerifier:
    def __init__(self, settings: BridgeSettings) -> None:
        self._settings = settings
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cache_ts: float | None = None

    async def decode(self, token: str) -> dict[str, Any]:
        try:
            header = jose_jwt.get_unverified_header(token)
        except JWTError as exc:
            raise TokenValidationError("Invalid token header") from exc

        kid = header.get("kid")
        jwks = await self._get_jwks_cached()
        key = self._find_jwk(jwks, kid)

        if key is None and kid:
            jwks = await self._refresh_jwks()
            key = self._find_jwk(jwks, kid)

        if key is None:
            raise TokenValidationError("Signing key not found")

        public_key = jose_jwk.construct(key).to_pem().decode("utf-8")
        audiences = (
            self._settings.audience
            if isinstance(self._settings.audience, tuple)
            else (self._settings.audience,)
        )
        last_error: JWTError | None = None
        for audience in audiences:
            try:
                decoded = jose_jwt.decode(
                    token,
                    key=public_key,
                    algorithms=list(self._settings.algorithms),
                    audience=audience,
                    issuer=self._settings.issuer,
                )
                if not isinstance(decoded, dict):
                    raise TokenValidationError("Decoded token payload is not an object")
                return decoded
            except JWTError as exc:
                last_error = exc

        raise TokenValidationError("Token validation failed") from last_error

    async def _fetch_jwks(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self._settings.jwks_url)
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
            raise TokenValidationError("Invalid JWKS response")
        return data

    async def _get_jwks_cached(self) -> dict[str, Any]:
        now = time.time()
        if (
            self._jwks_cache is not None
            and self._jwks_cache_ts is not None
            and now - self._jwks_cache_ts < self._settings.jwks_ttl_seconds
        ):
            return self._jwks_cache

        try:
            return await self._refresh_jwks()
        except httpx.HTTPError as exc:
            if self._jwks_cache is not None:
                return self._jwks_cache
            raise TokenValidationError("Failed to fetch JWKS") from exc

    async def _refresh_jwks(self) -> dict[str, Any]:
        data = await self._fetch_jwks()
        self._jwks_cache = data
        self._jwks_cache_ts = time.time()
        return data

    @staticmethod
    def _find_jwk(jwks: dict[str, Any], kid: str | None) -> dict[str, Any] | None:
        keys = jwks.get("keys", [])
        if not isinstance(keys, list):
            return None
        if kid:
            for key in keys:
                if isinstance(key, dict) and key.get("kid") == kid:
                    return key
        if len(keys) == 1 and isinstance(keys[0], dict):
            return keys[0]
        return None

