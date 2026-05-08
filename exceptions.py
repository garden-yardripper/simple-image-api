from typing import Mapping
from fastapi import HTTPException

class RateLimitedError(HTTPException):
    """429 response sent to a client when the allowed rate limit is exceeded (inherits from `HTTPException`)."""
    def __init__(
        self, message: str, retry_after: float,
        headers: Mapping[str, str] | None = None
    ) -> None:
        detail = {"message": message, "retry_after": retry_after}
        super().__init__(429, detail, headers)
        
class ApiKeyMissingError(HTTPException):
    """401 response sent to a client when the request's `api-key` header is missing (inherits from `HTTPException`)."""
    def __init__(
        self, message: str = "Missing API key",
        headers: Mapping[str, str] | None = None
    ) -> None:
        detail = {"message": message}
        super().__init__(401, detail, headers)