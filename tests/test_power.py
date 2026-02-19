"""Tests for power metrics functionality."""

import pytest
from unittest.mock import Mock
from idrac_power.power import get_power_metrics, format_power_output


def test_get_power_metrics():
    """Test power metrics extraction."""
    mock_client = Mock()
    
    # Mock chassis response
    mock_client.get.side_effect = [
        {
            "Members": [
                {"@odata.id": "/redfish/v1/Chassis/System.Embedded.1"}
            ]
        },
        {
            "PowerControl": [
                {
                    "PowerConsumedWatts": 245,
                    "AverageConsumedWatts": 230,
                    "PowerCapacityWatts": 750,
                    "MaxConsumedWatts": 380,
                    "PowerLimit": {"LimitInWatts": 500}
                }
            ],
            "PowerSupplies": [
                {
                    "Name": "PS1",
                    "Status": {"State": "Enabled", "Health": "OK"},
                    "PowerCapacityWatts": 750,
                    "LastPowerOutputWatts": 123
                }
            ]
        }
    ]
    
    metrics = get_power_metrics(mock_client)
    
    assert metrics["current_watts"] == 245
    assert metrics["average_watts"] == 230
    assert metrics["max_watts"] == 750
    assert metrics["chassis_id"] == "System.Embedded.1"
    assert len(metrics["power_supplies"]) == 1


def test_format_power_output_text():
    """Test text formatting of power metrics."""
    metrics = {
        "chassis_id": "System.Embedded.1",
        "current_watts": 245,
        "average_watts": 230,
        "max_consumed_watts": 380,
        "power_limit": 500,
        "max_watts": 750,
        "power_supplies": []
    }
    
    output = format_power_output(metrics, format="text")
    
    assert "Chassis: System.Embedded.1" in output
    assert "Current Power: 245 W" in output
    assert "Average Power: 230 W" in output


def test_format_power_output_json():
    """Test JSON formatting of power metrics."""
    import json
    
    metrics = {
        "chassis_id": "System.Embedded.1",
        "current_watts": 245,
        "power_supplies": []
    }
    
    output = format_power_output(metrics, format="json")
    parsed = json.loads(output)
    
    assert parsed["chassis_id"] == "System.Embedded.1"
    assert parsed["current_watts"] == 245
