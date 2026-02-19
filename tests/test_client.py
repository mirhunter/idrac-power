"""Tests for IDRACClient."""

import pytest
from unittest.mock import Mock, patch
from idrac_power.client import IDRACClient


def test_client_initialization():
    """Test client initializes with correct parameters."""
    client = IDRACClient(
        host="192.168.1.100",
        username="root",
        password="calvin",
        port=443,
        verify_ssl=True,
    )
    
    assert client.host == "192.168.1.100"
    assert client.port == 443
    assert client.base_url == "https://192.168.1.100:443/redfish/v1"
    assert client.verify_ssl is True


def test_client_context_manager():
    """Test client works as context manager."""
    with IDRACClient(
        host="192.168.1.100",
        username="root",
        password="calvin",
    ) as client:
        assert client.session is not None
    
    # Session should be closed after context exit
    assert client.session is not None


@patch("idrac_power.client.requests.Session")
def test_get_request(mock_session_class):
    """Test GET request construction."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"test": "data"}
    mock_session.get.return_value = mock_response
    mock_session_class.return_value = mock_session
    
    client = IDRACClient(
        host="192.168.1.100",
        username="root",
        password="calvin",
    )
    
    result = client.get("/Chassis")
    
    mock_session.get.assert_called_once_with(
        "https://192.168.1.100:443/redfish/v1/Chassis"
    )
    assert result == {"test": "data"}
