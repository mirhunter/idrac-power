"""SSH tunnel management for accessing iDRAC through jumphost."""

import logging
from typing import Optional
from sshtunnel import SSHTunnelForwarder
import paramiko


logger = logging.getLogger(__name__)


class SSHTunnel:
    """Manages SSH tunnel to iDRAC through a jumphost."""
    
    def __init__(
        self,
        jumphost: str,
        idrac_host: str,
        idrac_port: int = 443,
        jumphost_port: int = 22,
        jumphost_username: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        ssh_password: Optional[str] = None,
    ) -> None:
        """
        Initialize SSH tunnel configuration.
        
        Args:
            jumphost: Jumphost hostname (e.g., bastion.example.com)
            idrac_host: Target iDRAC IP or hostname
            idrac_port: Target iDRAC port (default: 443)
            jumphost_port: SSH port on jumphost (default: 22)
            jumphost_username: SSH username for jumphost
            ssh_key_path: Path to SSH private key
            ssh_password: SSH password (if not using key)
        """
        self.jumphost = jumphost
        self.idrac_host = idrac_host
        self.idrac_port = idrac_port
        self.jumphost_port = jumphost_port
        self.jumphost_username = jumphost_username
        self.ssh_key_path = ssh_key_path
        self.ssh_password = ssh_password
        self.tunnel: Optional[SSHTunnelForwarder] = None
        self.local_bind_port: Optional[int] = None
    
    def start(self) -> int:
        """
        Start the SSH tunnel.
        
        Returns:
            Local port number where the tunnel is listening
            
        Raises:
            Exception: If tunnel fails to start
        """
        # Build SSH authentication
        ssh_kwargs = {}
        if self.ssh_key_path:
            ssh_kwargs["ssh_pkey"] = self.ssh_key_path
        elif self.ssh_password:
            ssh_kwargs["ssh_password"] = self.ssh_password
        # else: let paramiko use default SSH key discovery (agent + ~/.ssh/id_*)
        
        self.tunnel = SSHTunnelForwarder(
            ssh_address_or_host=(self.jumphost, self.jumphost_port),
            ssh_username=self.jumphost_username,
            remote_bind_address=(self.idrac_host, self.idrac_port),
            local_bind_address=("127.0.0.1", 0),  # 0 = random available port
            **ssh_kwargs,
        )
        
        self.tunnel.start()
        self.local_bind_port = self.tunnel.local_bind_port
        
        logger.info(
            f"SSH tunnel established: localhost:{self.local_bind_port} -> "
            f"{self.jumphost} -> {self.idrac_host}:{self.idrac_port}"
        )
        
        return self.local_bind_port
    
    def stop(self) -> None:
        """Stop the SSH tunnel."""
        if self.tunnel:
            self.tunnel.stop()
            logger.info("SSH tunnel closed")
    
    def __enter__(self) -> "SSHTunnel":
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.stop()
