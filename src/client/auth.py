"""
Authentication Handler for AVEVA OSIsoft PI Web API.
Supports Basic Authentication, Windows Authentication (Kerberos/NTLM headers), and Mock Mode.
"""
from typing import Optional, Dict, Tuple
from requests.auth import HTTPBasicAuth
from config.settings import settings


class PIAuthHandler:
    """Manages authentication credentials and headers for PI Web API REST requests."""

    def __init__(
        self,
        auth_mode: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.auth_mode = (auth_mode or settings.PI_AUTH_MODE).lower()
        self.username = username or settings.PI_USERNAME
        self.password = password or settings.PI_PASSWORD

    def get_requests_auth(self) -> Optional[HTTPBasicAuth]:
        """Returns requests auth object (e.g. HTTPBasicAuth) if basic auth is configured."""
        if self.auth_mode == "basic" and self.username and self.password:
            return HTTPBasicAuth(self.username, self.password)
        return None

    def get_headers(self) -> Dict[str, str]:
        """Returns standard headers required by AVEVA PI Web API."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"  # Standard CSRF header for PI Web API
        }
        return headers

    def __repr__(self) -> str:
        return f"<PIAuthHandler mode={self.auth_mode} user={'***' if self.username else 'None'}>"
