from __future__ import annotations

import secrets
from typing import Any, Mapping

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.datastructures import Headers

from bearerbridge.config import BridgeSettings
from bearerbridge.errors import InternalServiceAuthError, TokenValidationError
from bearerbridge.jwks import JWKSVerifier

_security = HTTPBearer(auto_error=False)


class BearerBridge:
    def __init__(self, settings: BridgeSettings) -> None:
        self.settings = settings
        self._verifier = JWKSVerifier(settings)

    async def decode_token(self, token: str) -> dict[str, Any]:
        return await self._verifier.decode(token)

    async def require_user(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    ) -> dict[str, Any]:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        try:
            return await self.decode_token(credentials.credentials)
        except TokenValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc

    async def require_internal_service(self, request: Request) -> None:
        try:
            self.verify_internal_service(request.headers)
        except InternalServiceAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc

    async def require_user_and_internal_service(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    ) -> dict[str, Any]:
        await self.require_internal_service(request)
        return await self.require_user(credentials)

    def verify_internal_service(self, headers: Mapping[str, str] | Headers) -> None:
        expected = self.settings.internal_service_key
        if not expected:
            raise InternalServiceAuthError("Internal service key is not configured")

        provided = headers.get(self.settings.internal_header_name)
        if not provided or not secrets.compare_digest(provided, expected):
            raise InternalServiceAuthError("Invalid internal service key")

    def forward_headers(self, inbound_headers: Mapping[str, str] | Headers) -> dict[str, str]:
        headers: dict[str, str] = {}
        authorization = inbound_headers.get("authorization") or inbound_headers.get("Authorization")
        if authorization:
            headers["Authorization"] = authorization
        if self.settings.internal_service_key:
            headers[self.settings.internal_header_name] = self.settings.internal_service_key
        return headers
