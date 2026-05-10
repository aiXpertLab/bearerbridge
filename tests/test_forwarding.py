from bearerbridge.config import BridgeSettings
from bearerbridge.dependencies import BearerBridge


def test_forward_headers_adds_internal_key_and_preserves_authorization() -> None:
    bridge = BearerBridge(
        BridgeSettings(
            jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
            issuer="https://example.supabase.co/auth/v1",
            internal_service_key="secret",
        )
    )

    headers = bridge.forward_headers({"authorization": "Bearer abc"})

    assert headers == {
        "Authorization": "Bearer abc",
        "X-Internal-Service-Key": "secret",
    }


def test_verify_internal_service_accepts_matching_key() -> None:
    bridge = BearerBridge(
        BridgeSettings(
            jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
            issuer="https://example.supabase.co/auth/v1",
            internal_service_key="secret",
        )
    )

    bridge.verify_internal_service({"X-Internal-Service-Key": "secret"})
