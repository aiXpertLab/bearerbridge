class BearerBridgeError(Exception):
    """Base package exception."""


class TokenValidationError(BearerBridgeError):
    """Raised when bearer JWT validation fails."""


class InternalServiceAuthError(BearerBridgeError):
    """Raised when internal service authentication fails."""
