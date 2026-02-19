"""CLI interface for iDRAC power monitoring."""

import os
import sys
import json
import re
from typing import Optional

import click

from .client import IDRACClient
from .power import get_power_metrics, format_power_output
from .tunnel import SSHTunnel
from .monitor import PowerMonitor
from .multi import (
    load_servers_from_csv,
    monitor_multiple_servers,
    format_multi_server_output,
)


def format_duration(hours: float) -> str:
    """
    Format hours into human-friendly duration string.
    
    Args:
        hours: Duration in hours
        
    Returns:
        Formatted string like "5m", "2h", "1d"
        
    Examples:
        0.0833 -> "5m"
        1.5 -> "1.5h"
        24.0 -> "1d"
    """
    # Try days
    if hours >= 24 and hours % 24 == 0:
        days = int(hours / 24)
        return f"{days}d"
    
    # Try hours
    if hours >= 1:
        if hours == int(hours):
            return f"{int(hours)}h"
        return f"{hours:.1f}h"
    
    # Try minutes
    minutes = hours * 60
    if minutes >= 1:
        if minutes == int(minutes):
            return f"{int(minutes)}m"
        return f"{minutes:.1f}m"
    
    # Seconds
    seconds = hours * 3600
    if seconds == int(seconds):
        return f"{int(seconds)}s"
    return f"{seconds:.1f}s"


def parse_duration(duration_str: str) -> float:
    """
    Parse human-friendly duration string to hours.
    
    Args:
        duration_str: Duration like "5m", "3h", "1d", "24", "0.5h"
        
    Returns:
        Duration in hours
        
    Examples:
        "5m" -> 0.0833 (5 minutes)
        "3h" -> 3.0
        "1d" -> 24.0
        "30s" -> 0.00833 (30 seconds)
        "24" -> 24.0 (plain number assumes hours)
    """
    duration_str = str(duration_str).strip().lower()
    
    # Match number followed by optional unit
    match = re.match(r'^([\d.]+)([smhd])?$', duration_str)
    if not match:
        raise click.BadParameter(
            f"Invalid duration format: '{duration_str}'. "
            "Use formats like: 5m, 3h, 1d, 24, 0.5h"
        )
    
    value = float(match.group(1))
    unit = match.group(2) or 'h'  # Default to hours if no unit
    
    # Convert to hours
    conversions = {
        's': value / 3600,  # seconds to hours
        'm': value / 60,     # minutes to hours
        'h': value,          # hours
        'd': value * 24,     # days to hours
    }
    
    return conversions[unit]


@click.command()
@click.option(
    "--host",
    envvar="IDRAC_HOST",
    help="iDRAC hostname or IP address (not needed with --servers-file)",
)
@click.option(
    "--username",
    "-u",
    envvar="IDRAC_USERNAME",
    help="iDRAC username (not needed with --servers-file)",
)
@click.option(
    "--password",
    "-p",
    envvar="IDRAC_PASSWORD",
    help="iDRAC password (not needed with --servers-file)",
)
@click.option(
    "--port",
    default=443,
    envvar="IDRAC_PORT",
    help="iDRAC HTTPS port (default: 443)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format",
)
@click.option(
    "--verify-ssl/--no-verify-ssl",
    default=True,
    help="Verify SSL certificates (default: yes)",
)
@click.option(
    "--jumphost",
    envvar="IDRAC_JUMPHOST",
    help="SSH jumphost to tunnel through (optional)",
)
@click.option(
    "--jumphost-user",
    envvar="IDRAC_JUMPHOST_USER",
    help="SSH username for jumphost (defaults to current user)",
)
@click.option(
    "--ssh-key",
    envvar="IDRAC_JUMPHOST_SSH_KEY",
    help="Path to SSH private key for jumphost (optional, uses SSH agent/default keys if not specified)",
)
@click.option(
    "--ssh-password",
    envvar="IDRAC_JUMPHOST_SSH_PASSWORD",
    help="SSH password for jumphost (only needed if not using SSH keys)",
)
@click.option(
    "--no-tunnel",
    is_flag=True,
    help="Disable SSH tunnel (for direct iDRAC access)",
)
@click.option(
    "--monitor",
    type=str,
    metavar="DURATION",
    help="Monitor and average power over duration (e.g., 24h, 30m, 1d)",
)
@click.option(
    "--sample-interval",
    type=str,
    default="5m",
    metavar="INTERVAL",
    help="Sample interval for monitoring mode (e.g., 5m, 10m, 1h) - default: 5m",
)
@click.option(
    "--servers-file",
    type=click.Path(exists=True),
    metavar="CSV_FILE",
    help="CSV file with server list (columns: ip,username,password,name)",
)
@click.option(
    "--max-workers",
    type=int,
    default=5,
    help="Max parallel connections for multi-server mode (default: 5)",
)
@click.option(
    "--output",
    type=click.Path(),
    metavar="FILENAME",
    help="Save report to file (extension added automatically: .txt or .json)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress progress messages (errors and final report still shown)",
)
@click.version_option()
def main(
    host: str,
    username: str,
    password: str,
    port: int,
    output_format: str,
    verify_ssl: bool,
    jumphost: Optional[str],
    jumphost_user: Optional[str],
    ssh_key: Optional[str],
    ssh_password: Optional[str],
    no_tunnel: bool,
    monitor: Optional[str],
    sample_interval: str,
    servers_file: Optional[str],
    max_workers: int,
    output: Optional[str],
    quiet: bool,
) -> None:
    """Connect to Dell iDRAC and retrieve current power usage."""
    try:
        # Multi-server mode
        if servers_file:
            servers = load_servers_from_csv(servers_file)
            
            # Parse durations if monitoring
            duration_hours = None
            interval_minutes = None
            if monitor:
                duration_hours = parse_duration(monitor)
                interval_hours = parse_duration(sample_interval)
                interval_minutes = int(interval_hours * 60)
            
            # Monitor all servers
            results = monitor_multiple_servers(
                servers=servers,
                jumphost=jumphost if not no_tunnel else None,
                jumphost_user=jumphost_user,
                ssh_key=ssh_key,
                ssh_password=ssh_password,
                verify_ssl=verify_ssl,
                monitor_hours=duration_hours,
                sample_interval_minutes=interval_minutes,
                max_workers=max_workers,
                quiet=quiet,
            )
            
            # Format and display results
            output_text = format_multi_server_output(results, output_format)
            
            # Write to file if requested
            if output:
                output_file = output
                if not output_file.endswith(('.txt', '.json')):
                    # Add extension based on format
                    ext = '.json' if output_format.lower() == 'json' else '.txt'
                    output_file = f"{output_file}{ext}"
                
                with open(output_file, 'w') as f:
                    f.write(output_text)
                if not quiet:
                    click.echo(f"Report saved to: {output_file}", err=True)
            
            # Also print to stdout
            click.echo(output_text)
            
            # Exit with error if any servers failed
            if any(not r['success'] for r in results):
                sys.exit(1)
            
            return
        
        # Single server mode - validate required options
        if not host or not username or not password:
            raise click.UsageError(
                "Either --servers-file or all of --host, --username, and --password are required"
            )
        
        # Single server mode (existing code)
        # Determine if we need to use SSH tunnel
        tunnel = None
        actual_host = host
        actual_port = port
        
        if jumphost and not no_tunnel:
            # Create and start SSH tunnel
            tunnel = SSHTunnel(
                jumphost=jumphost,
                idrac_host=host,
                idrac_port=port,
                jumphost_username=jumphost_user,
                ssh_key_path=ssh_key,
                ssh_password=ssh_password,
            )
            local_port = tunnel.start()
            actual_host = "127.0.0.1"
            actual_port = local_port
            if not quiet:
                click.echo(f"SSH tunnel: localhost:{local_port} -> {jumphost} -> {host}:{port}", err=True)
        elif no_tunnel and jumphost:
            if not quiet:
                click.echo("Warning: --no-tunnel specified, ignoring --jumphost", err=True)
        
        try:
            client = IDRACClient(
                host=actual_host,
                username=username,
                password=password,
                port=actual_port,
                verify_ssl=verify_ssl,
                original_host=host if tunnel else None,
            )
            
            if monitor:
                # Parse duration strings
                duration_hours = parse_duration(monitor)
                interval_hours = parse_duration(sample_interval)
                interval_minutes = int(interval_hours * 60)
                
                # Monitoring mode - collect samples over time
                power_monitor = PowerMonitor(
                    client=client,
                    duration_hours=duration_hours,
                    sample_interval_minutes=interval_minutes,
                    quiet=quiet,
                )
                averages = power_monitor.run()
                
                # Format output
                if output_format.lower() == "json":
                    output_text = json.dumps(averages, indent=2)
                else:
                    output_text = format_monitoring_output(averages)
            else:
                # Single reading mode
                power_metrics = get_power_metrics(client)
                output_text = format_power_output(power_metrics, format=output_format)
            
            # Write to file if requested (single server mode)
            if output:
                output_file = output
                if not output_file.endswith(('.txt', '.json')):
                    # Add extension based on format
                    ext = '.json' if output_format.lower() == 'json' else '.txt'
                    output_file = f"{output_file}{ext}"
                
                with open(output_file, 'w') as f:
                    f.write(output_text)
                if not quiet:
                    click.echo(f"Report saved to: {output_file}", err=True)
            
            # Also print to stdout
            click.echo(output_text)
        finally:
            if tunnel:
                tunnel.stop()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def format_monitoring_output(averages: dict) -> str:
    """Format monitoring averages for text output."""
    duration_str = format_duration(averages['monitoring_duration_hours'])
    interval_str = format_duration(averages['sample_interval_minutes'] / 60)
    
    lines = [
        f"=== {duration_str} Power Monitoring Results ===",
        f"Samples: {averages['sample_count']} (every {interval_str})",
        f"Period: {averages['start_time']} to {averages['end_time']}",
        "",
        f"System Average: {averages['system_average_watts']} W",
        f"System Min: {averages['system_min_watts']} W",
        f"System Max: {averages['system_max_watts']} W",
        "",
        "Power Supply Averages:",
    ]
    
    for psu in averages.get("power_supplies", []):
        status = f"{psu.get('state')} - {psu.get('health')}" if psu.get('state') else "Unknown"
        lines.append(f"  {psu['name']}: {status}")
        if psu.get('capacity_watts'):
            lines.append(f"    Capacity: {psu['capacity_watts']} W")
        if psu.get('average_output_watts') is not None:
            lines.append(f"    Average Output: {psu['average_output_watts']} W")
            lines.append(f"    Min/Max Output: {psu['min_output_watts']} / {psu['max_output_watts']} W")
        if psu.get('average_input_watts') is not None:
            lines.append(f"    Average Input: {psu['average_input_watts']} W")
            lines.append(f"    Min/Max Input: {psu['min_input_watts']} / {psu['max_input_watts']} W")
        if psu.get('average_efficiency_percent') is not None:
            lines.append(f"    Average Efficiency: {psu['average_efficiency_percent']}%")
    
    return "\n".join(lines)


if __name__ == "__main__":
    main()
