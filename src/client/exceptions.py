"""
Custom Exception Hierarchy for PI Web API and Industrial Data Validation.
Enables precise troubleshooting and error isolation during plant data ingestion.
"""


class PIException(Exception):
    """Base exception for all PI System and Data Ingestion operations."""
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class PIConnectionError(PIException):
    """Raised when network connection to the PI Web API server fails or times out."""
    pass


class PIAuthenticationError(PIException):
    """Raised when PI Web API rejects credentials (HTTP 401 Unauthorized or 403 Forbidden)."""
    pass


class PINotFoundError(PIException):
    """Raised when requested PI Point, WebID, AF Element, or Stream does not exist (HTTP 404)."""
    pass


class PIResponseError(PIException):
    """Raised when PI Web API returns an HTTP 5xx error or invalid JSON structure."""
    pass


class PITimeoutError(PIConnectionError):
    """Raised when PI Web API request times out."""
    pass


class PIConfigurationError(PIException):
    """Raised when required configuration settings or tags are missing/invalid."""
    pass
