"""HTTP-mappable lifecycle errors."""


class SessionNotFoundError(LookupError):
    """Raised when a session is not found. Intended to map to HTTP 404."""

    def __init__(self, message: str, *, status: str | None = None) -> None:
        super().__init__(message)
        self.status = status



class SessionConflictError(RuntimeError):
    """Wrong status / out-of-order respond (maps to HTTP 409)."""

    def __init__(self, message: str, *, status: str | None = None) -> None:
        super().__init__(message)
        self.status = status
