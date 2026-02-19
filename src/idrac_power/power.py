"""Power metrics retrieval and formatting."""

import json
from typing import Any, Dict

from .client import IDRACClient


def get_power_metrics(client: IDRACClient) -> Dict[str, Any]:
    """
    Retrieve power metrics from iDRAC.
    
    Args:
        client: Authenticated IDRACClient instance
        
    Returns:
        Dictionary containing power metrics
        
    Raises:
        requests.RequestException: On API errors
    """
    # Get chassis information
    chassis_response = client.get("/Chassis")
    chassis_members = chassis_response.get("Members", [])
    
    if not chassis_members:
        raise ValueError("No chassis found")
    
    # Typically System.Embedded.1 for Dell servers
    chassis_id = chassis_members[0]["@odata.id"].split("/")[-1]
    
    # Get power information
    power_data = client.get(f"/Chassis/{chassis_id}/Power")
    
    # Extract relevant metrics
    power_control = power_data.get("PowerControl", [{}])[0]
    
    # Check PowerMetrics for average data (Dell OEM extension)
    power_metrics = power_control.get("PowerMetrics", {})
    
    metrics = {
        "current_watts": int(power_control.get("PowerConsumedWatts")) if power_control.get("PowerConsumedWatts") else None,
        "average_watts": int(power_metrics.get("AverageConsumedWatts")) if power_metrics.get("AverageConsumedWatts") else None,
        "max_watts": int(power_control.get("PowerCapacityWatts")) if power_control.get("PowerCapacityWatts") else None,
        "min_watts": int(power_metrics.get("MinConsumedWatts")) if power_metrics.get("MinConsumedWatts") else None,
        "max_consumed_watts": int(power_metrics.get("MaxConsumedWatts")) if power_metrics.get("MaxConsumedWatts") else None,
        "power_limit": power_control.get("PowerLimit", {}).get("LimitInWatts"),
        "chassis_id": chassis_id,
        "average_interval_min": power_metrics.get("IntervalInMin"),
    }
    
    # Add power supply information if available
    power_supplies = power_data.get("PowerSupplies", [])
    metrics["power_supplies"] = [
        {
            "name": ps.get("Name"),
            "state": ps.get("Status", {}).get("State"),
            "health": ps.get("Status", {}).get("Health"),
            "capacity_watts": int(ps.get("PowerCapacityWatts")) if ps.get("PowerCapacityWatts") else None,
            "last_power_output": int(ps.get("LastPowerOutputWatts")) if ps.get("LastPowerOutputWatts") else None,
            "input_watts": int(ps.get("PowerInputWatts")) if ps.get("PowerInputWatts") else None,
            "output_watts": int(ps.get("PowerOutputWatts")) if ps.get("PowerOutputWatts") else None,
            "efficiency_percent": round(ps.get("EfficiencyPercent"), 1) if ps.get("EfficiencyPercent") else None,
            "line_input_voltage": ps.get("LineInputVoltage"),
        }
        for ps in power_supplies
    ]
    
    # Add redundancy information
    redundancy = power_data.get("Redundancy", [])
    if redundancy:
        red = redundancy[0]
        metrics["redundancy"] = {
            "mode": red.get("Mode"),
            "status": red.get("Status", {}).get("Health"),
            "min_needed": red.get("MinNumNeeded"),
            "max_supported": red.get("MaxNumSupported"),
        }
    
    return metrics


def format_power_output(metrics: Dict[str, Any], format: str = "text") -> str:
    """
    Format power metrics for display.
    
    Args:
        metrics: Power metrics dictionary
        format: Output format ('text' or 'json')
        
    Returns:
        Formatted string output
    """
    if format.lower() == "json":
        return json.dumps(metrics, indent=2)
    
    # Text format
    lines = [
        f"Chassis: {metrics['chassis_id']}",
    ]
    
    # Use average for UPS sizing, fallback to current if unavailable
    primary_watts = metrics.get("average_watts") or metrics.get("current_watts")
    if primary_watts:
        label = "Average Power" if metrics.get("average_watts") else "Current Power"
        interval = f" ({metrics.get('average_interval_min')}min avg)" if metrics.get("average_interval_min") else ""
        lines.append(f"{label}: {primary_watts} W{interval}")
    
    # Show both if we have both
    if metrics.get("average_watts") and metrics.get("current_watts"):
        lines.append(f"Current Power: {metrics['current_watts']} W")
    
    if metrics.get("max_consumed_watts"):
        lines.append(f"Peak Power: {metrics['max_consumed_watts']} W")
    
    if metrics.get("power_limit"):
        lines.append(f"Power Limit: {metrics['power_limit']} W")
    
    if metrics.get("max_watts"):
        lines.append(f"Max Capacity: {metrics['max_watts']} W")
    
    # Show redundancy mode
    if metrics.get("redundancy"):
        red = metrics["redundancy"]
        lines.append(f"\nRedundancy: {red['mode']} ({red['status']}) - {red['min_needed']}/{red['max_supported']} PSUs needed")
    
    # Power supply status
    if metrics.get("power_supplies"):
        lines.append("\nPower Supplies:")
        for ps in metrics["power_supplies"]:
            status = f"{ps['state']} - {ps['health']}" if ps.get('state') else "Unknown"
            lines.append(f"  {ps['name']}: {status}")
            if ps.get('capacity_watts') is not None:
                lines.append(f"    Capacity: {ps['capacity_watts']} W")
            
            # Always show output (even if 0 or N/A)
            if ps.get('output_watts') is not None:
                lines.append(f"    Output: {ps['output_watts']} W")
            else:
                lines.append(f"    Output: N/A")
            
            # Always show input if available
            if ps.get('input_watts') is not None:
                lines.append(f"    Input: {ps['input_watts']} W")
            
            # Show efficiency if available
            if ps.get('efficiency_percent') is not None:
                lines.append(f"    Efficiency: {ps['efficiency_percent']}%")
    
    return "\n".join(lines)
