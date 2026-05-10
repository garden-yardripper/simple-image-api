from typing import Mapping
from fastapi import HTTPException
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse

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
        
class ApiKeyInvalidError(HTTPException):
    """401 response sent to a client when the request's `api-key` header 
    is invalid/not found in DB (inherits from `HTTPException`)."""
    def __init__(
        self, message: str = "Invalid API key",
        headers: Mapping[str, str] | None = None
    ) -> None:
        detail = {"message": message}
        super().__init__(401, detail, headers)

class RateLimitInfoResponse(JSONResponse):
    """JSON response sent to a client with added rate limiting info."""
    def __init__(
        self, content: dict,
        ratelimit_remaining: int,
        ratelimit_reset: float,
        status_code: int = 200, 
        headers: Mapping[str, str] | None = None, 
        media_type: str | None = None, 
        background: BackgroundTask | None = None
    ) -> None:
        content["ratelimit-remaining"] = ratelimit_remaining
        content["ratelimit-reset"] = ratelimit_reset
        super().__init__(content, status_code, headers, media_type, background)