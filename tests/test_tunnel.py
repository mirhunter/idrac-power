"""Tests for SSH tunnel functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from idrac_power.tunnel import SSHTunnel


@patch("idrac_power.tunnel.SSHTunnelForwarder")
def test_tunnel_initialization(mock_tunnel_class):
    """Test tunnel initializes with correct parameters."""
    tunnel = SSHTunnel(
        jumphost="bastion.example.com",
        idrac_host="10.1.2.3",
        idrac_port=443,
        jumphost_username="testuser",
        ssh_key_path="/home/user/.ssh/id_rsa",
    )
    
    assert tunnel.jumphost == "bastion.example.com"
    assert tunnel.idrac_host == "10.1.2.3"
    assert tunnel.idrac_port == 443
    assert tunnel.jumphost_username == "testuser"


@patch("idrac_power.tunnel.SSHTunnelForwarder")
def test_tunnel_start(mock_tunnel_class):
    """Test tunnel start establishes connection."""
    mock_tunnel_instance = MagicMock()
    mock_tunnel_instance.local_bind_port = 54321
    mock_tunnel_class.return_value = mock_tunnel_instance
    
    tunnel = SSHTunnel(
        jumphost="bastion.example.com",
        idrac_host="10.1.2.3",
        jumphost_username="testuser",
        ssh_key_path="/home/user/.ssh/id_rsa",
    )
    
    local_port = tunnel.start()
    
    assert local_port == 54321
    mock_tunnel_instance.start.assert_called_once()
    mock_tunnel_class.assert_called_once()


@patch("idrac_power.tunnel.SSHTunnelForwarder")
def test_tunnel_context_manager(mock_tunnel_class):
    """Test tunnel works as context manager."""
    mock_tunnel_instance = MagicMock()
    mock_tunnel_instance.local_bind_port = 54321
    mock_tunnel_class.return_value = mock_tunnel_instance
    
    with SSHTunnel(
        jumphost="bastion.example.com",
        idrac_host="10.1.2.3",
        jumphost_username="testuser",
        ssh_key_path="/home/user/.ssh/id_rsa",
    ) as tunnel:
        assert tunnel.local_bind_port == 54321
    
    mock_tunnel_instance.start.assert_called_once()
    mock_tunnel_instance.stop.assert_called_once()


@patch("idrac_power.tunnel.SSHTunnelForwarder")
def test_tunnel_with_password(mock_tunnel_class):
    """Test tunnel initialization with password instead of key."""
    mock_tunnel_instance = MagicMock()
    mock_tunnel_instance.local_bind_port = 54321
    mock_tunnel_class.return_value = mock_tunnel_instance
    
    tunnel = SSHTunnel(
        jumphost="bastion.example.com",
        idrac_host="10.1.2.3",
        jumphost_username="testuser",
        ssh_password="secretpass",
    )
    
    tunnel.start()
    
    # Verify password was passed
    call_kwargs = mock_tunnel_class.call_args[1]
    assert "ssh_password" in call_kwargs
    assert call_kwargs["ssh_password"] == "secretpass"
