"""iDRAC client for Redfish API communication."""

from typing import Any, Dict, Optional
import requests
from urllib3.exceptions import InsecureRequestWarning


class IDRACClient:
    """Client for communicating with Dell iDRAC via Redfish API."""
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        verify_ssl: bool = True,
        original_host: Optional[str] = None,
    ) -> None:
        """
        Initialize iDRAC client.
        
        Args:
            host: iDRAC hostname or IP address (or localhost if tunneled)
            username: Authentication username
            password: Authentication password
            port: HTTPS port (default: 443)
            verify_ssl: Whether to verify SSL certificates
            original_host: Original iDRAC host for Host header (when tunneling)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.original_host = original_host or host
        self.base_url = f"https://{host}:{port}/redfish/v1"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = verify_ssl
        
        # Set Host header to original iDRAC host when tunneling
        if original_host:
            self.session.headers.update({'Host': original_host})
        
        if not verify_ssl:
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    
    def get(self, endpoint: str) -> Dict[str, Any]:
        """
        Make a GET request to the Redfish API.
        
        Args:
            endpoint: API endpoint path (e.g., '/Chassis/System.Embedded.1/Power')
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.RequestException: On connection or HTTP errors
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self) -> "IDRACClient":
        """Context manager entry."""
        return self
    
    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
