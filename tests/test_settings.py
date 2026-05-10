from bearerbridge.config import BridgeSettings


def test_settings_requires_jwks_url() -> None:
    try:
        BridgeSettings(jwks_url="", issuer="issuer")
    except ValueError as exc:
        assert "jwks_url" in str(exc)
    else:
        raise AssertionError("expected ValueError")
