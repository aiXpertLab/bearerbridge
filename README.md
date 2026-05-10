# BearerBridge

BearerBridge is a small FastAPI auth helper for teams that pass user bearer tokens across multiple services.
It validates Supabase/JWKS access tokens at each service boundary and adds a simple internal service key check for service-to-service calls.

```text
frontend -> core API -> agent API -> MCP API -> core API
           JWT + internal key all the way across trusted service hops
```

BearerBridge does not generate users, store secrets, or replace your identity provider. It helps your APIs consistently answer two questions:

```text
Who is the user?        Authorization: Bearer <user jwt>
Is this our service?    X-Internal-Service-Key: <shared service secret>
```

## Features

- Validate bearer JWTs from Supabase or any JWKS-compatible issuer.
- Verify issuer, audience, expiration, signature, and allowed algorithms.
- Cache JWKS responses with automatic refresh when a new `kid` appears.
- FastAPI dependencies for user JWT auth, internal service auth, or both together.
- Constant-time internal service key comparison using `secrets.compare_digest`.
- Header forwarding helper for chained service calls.
- Framework-light core with only `fastapi`, `httpx`, and `python-jose` runtime dependencies.
- MIT licensed and safe for public reuse; secrets stay in environment variables, not in the package.

## Installation

```bash
pip install bearerbridge
```

For local development from this repo:

```bash
pip install -e .[dev]
```

## Quick Start

```python
from typing import Any

from fastapi import Depends, FastAPI, Request
from bearerbridge import BearerBridge, BridgeSettings

bridge = BearerBridge(
    BridgeSettings(
        jwks_url="https://PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json",
        issuer="https://PROJECT_REF.supabase.co/auth/v1",
        audience="authenticated",
        algorithms=("ES256", "RS256"),
        internal_service_key="use-a-long-random-secret-from-env",
    )
)

app = FastAPI()

@app.get("/me")
async def me(claims: dict[str, Any] = Depends(bridge.require_user)):
    return {"sub": claims.get("sub"), "email": claims.get("email")}

@app.post("/internal/run")
async def run_internal(
    claims: dict[str, Any] = Depends(bridge.require_user_and_internal_service),
):
    return {"ok": True, "user_id": claims.get("sub")}
```

## Environment Example

BearerBridge intentionally does not read your environment by itself. Your app should load settings however it already does, then pass them into `BridgeSettings`.

```env
JWKS_URL=https://PROJECT_REF.supabase.co/auth/v1/.well-known/jwks.json
JWKS_ISS=https://PROJECT_REF.supabase.co/auth/v1
JWKS_AUD=authenticated
JWKS_ALG=ES256,RS256
INTERNAL_SERVICE_KEY=generate-a-long-random-secret
```

Generate a service key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use the same `INTERNAL_SERVICE_KEY` in services that are allowed to call each other. Do not expose it to browsers.

## Forwarding Auth Headers

When one service calls the next service, forward the user JWT and add your internal service key:

```python
import httpx
from fastapi import Request
from bearerbridge import BearerBridge, BridgeSettings

bridge = BearerBridge(BridgeSettings(...))

async def call_agent(request: Request, payload: dict):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://agent.example.com/run_tool",
            json=payload,
            headers=bridge.forward_headers(request.headers),
        )
        response.raise_for_status()
        return response.json()
```

`forward_headers` copies the inbound `Authorization` header and adds `X-Internal-Service-Key` when configured.

## Common Service Chain

For a public multi-service chain, validate at every public service boundary:

```text
React app
  -> Core API: validates user JWT
  -> Agent API: validates user JWT + internal service key
  -> MCP API: validates user JWT + internal service key
  -> Core API: validates user JWT + internal service key for internal callbacks
```

Public health endpoints can stay unauthenticated for load balancers. Business endpoints should require at least the user JWT, and service-only endpoints should require both JWT and internal service key.

## API

### `BridgeSettings`

```python
BridgeSettings(
    jwks_url: str,
    issuer: str,
    audience: str | tuple[str, ...] = "authenticated",
    algorithms: tuple[str, ...] = ("ES256", "RS256"),
    jwks_ttl_seconds: int = 36000,
    internal_service_key: str | None = None,
    internal_header_name: str = "X-Internal-Service-Key",
)
```

### `BearerBridge`

```python
await bridge.decode_token(token)
await bridge.require_user(...)
await bridge.require_internal_service(...)
await bridge.require_user_and_internal_service(...)
bridge.forward_headers(inbound_headers)
```

## Security Notes

- Never put `INTERNAL_SERVICE_KEY` in frontend code.
- Prefer HTTPS everywhere.
- Use a long random service key and rotate it when team access changes.
- Keep JWT validation enabled in each separately reachable service.
- Do not trust decoded JWT claims unless signature, issuer, audience, algorithm, and expiry were verified.
- BearerBridge validates authentication; your app still owns authorization decisions such as tenant access, roles, and row-level security.

## Publishing

Build:

```bash
python -m build
```

Check:

```bash
python -m twine check dist/*
```

Publish to TestPyPI first:

```bash
python -m twine upload --repository testpypi dist/*
```

Publish to PyPI:

```bash
python -m twine upload dist/*
```

## License

MIT

