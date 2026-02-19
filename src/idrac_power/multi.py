"""Multi-server monitoring for batch operations."""

import csv
import concurrent.futures
from typing import List, Dict, Optional
from pathlib import Path

import click

from .client import IDRACClient
from .power import get_power_metrics
from .tunnel import SSHTunnel
from .monitor import PowerMonitor


def format_duration(hours: float) -> str:
    """Format hours into human-friendly duration string."""
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


def load_servers_from_csv(csv_file: str) -> List[Dict[str, str]]:
    """
    Load server credentials from CSV file.
    
    Args:
        csv_file: Path to CSV file with columns: ip,username,password
                  Optional columns: name, port, jumphost, jumphost_user, 
                                   jumphost_ssh_key, jumphost_ssh_password
    
    Returns:
        List of server dictionaries
        
    Example CSV:
        ip,username,password,name,jumphost,jumphost_user
        192.0.2.10,root,pass1,server1,jump1.example.com,admin
        192.0.2.11,root,pass2,server2,jump2.example.com,admin
        192.0.2.12,root,pass3,server3,,,  # No jumphost for this server
    """
    servers = []
    csv_path = Path(csv_file)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Server file not found: {csv_file}")
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        # Validate required columns
        required = {'ip', 'username', 'password'}
        if not required.issubset(reader.fieldnames):
            raise ValueError(
                f"CSV must contain columns: {', '.join(required)}\n"
                f"Found: {', '.join(reader.fieldnames)}"
            )
        
        for row in reader:
            server = {
                'ip': row['ip'].strip(),
                'username': row['username'].strip(),
                'password': row['password'].strip(),
                'name': row.get('name', row['ip']).strip() if row.get('name', '').strip() else row['ip'],
                'port': int(row.get('port', 443)) if row.get('port', '').strip() else 443,
                # Jumphost configuration (per-server)
                'jumphost': row.get('jumphost', '').strip() or None,
                'jumphost_user': row.get('jumphost_user', '').strip() or None,
                'jumphost_ssh_key': row.get('jumphost_ssh_key', '').strip() or None,
                'jumphost_ssh_password': row.get('jumphost_ssh_password', '').strip() or None,
            }
            servers.append(server)
    
    return servers


def monitor_single_server(
    server: Dict[str, str],
    jumphost: Optional[str],
    jumphost_user: Optional[str],
    ssh_key: Optional[str],
    ssh_password: Optional[str],
    verify_ssl: bool,
    monitor_hours: Optional[float] = None,
    sample_interval_minutes: Optional[int] = None,
    quiet: bool = False,
) -> Dict:
    """
    Monitor a single server and return results.
    
    Args:
        server: Server configuration dict (may include per-server jumphost config)
        jumphost: Global SSH jumphost (overridden by server-specific config)
        jumphost_user: Global SSH username (overridden by server-specific config)
        ssh_key: Global SSH key path (overridden by server-specific config)
        ssh_password: Global SSH password (overridden by server-specific config)
        verify_ssl: Verify SSL certificates
        monitor_hours: Monitoring duration in hours (None for single reading)
        sample_interval_minutes: Sample interval in minutes
        quiet: Suppress progress messages
        
    Returns:
        Dictionary with server name and metrics/error
    """
    result = {
        'name': server['name'],
        'ip': server['ip'],
        'success': False,
        'error': None,
        'metrics': None,
    }
    
    tunnel = None
    
    try:
        # Setup connection (with or without tunnel)
        actual_host = server['ip']
        actual_port = server['port']
        
        # Use per-server jumphost config if available, otherwise use global
        server_jumphost = server.get('jumphost') or jumphost
        server_jumphost_user = server.get('jumphost_user') or jumphost_user
        server_ssh_key = server.get('jumphost_ssh_key') or ssh_key
        server_ssh_password = server.get('jumphost_ssh_password') or ssh_password
        
        if server_jumphost:
            tunnel = SSHTunnel(
                jumphost=server_jumphost,
                idrac_host=server['ip'],
                idrac_port=server['port'],
                jumphost_username=server_jumphost_user,
                ssh_key_path=server_ssh_key,
                ssh_password=server_ssh_password,
            )
            local_port = tunnel.start()
            actual_host = "127.0.0.1"
            actual_port = local_port
        
        # Create client
        client = IDRACClient(
            host=actual_host,
            username=server['username'],
            password=server['password'],
            port=actual_port,
            verify_ssl=verify_ssl,
            original_host=server['ip'] if tunnel else None,
        )
        
        # Get metrics (single reading or monitoring)
        if monitor_hours:
            # Monitoring mode
            power_monitor = PowerMonitor(
                client=client,
                duration_hours=monitor_hours,
                sample_interval_minutes=sample_interval_minutes,
                quiet=quiet,
            )
            if not quiet:
                click.echo(f"[{server['name']}] Starting monitoring...", err=True)
            metrics = power_monitor.run()
        else:
            # Single reading
            metrics = get_power_metrics(client)
        
        result['success'] = True
        result['metrics'] = metrics
        
    except Exception as e:
        result['error'] = str(e)
        if not quiet:
            click.echo(f"[{server['name']}] Error: {e}", err=True)
    
    finally:
        if tunnel:
            tunnel.stop()
    
    return result


def monitor_multiple_servers(
    servers: List[Dict[str, str]],
    jumphost: Optional[str],
    jumphost_user: Optional[str],
    ssh_key: Optional[str],
    ssh_password: Optional[str],
    verify_ssl: bool,
    monitor_hours: Optional[float] = None,
    sample_interval_minutes: Optional[int] = None,
    max_workers: int = 5,
    quiet: bool = False,
) -> List[Dict]:
    """
    Monitor multiple servers in parallel.
    
    Args:
        servers: List of server configurations
        jumphost: SSH jumphost
        jumphost_user: SSH username
        ssh_key: SSH key path
        ssh_password: SSH password
        verify_ssl: Verify SSL certificates
        monitor_hours: Monitoring duration in hours
        sample_interval_minutes: Sample interval in minutes
        max_workers: Maximum parallel workers
        quiet: Suppress progress messages
        
    Returns:
        List of results for each server
    """
    if not quiet:
        click.echo(f"Monitoring {len(servers)} server(s)...\n", err=True)
    
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_server = {
            executor.submit(
                monitor_single_server,
                server,
                jumphost,
                jumphost_user,
                ssh_key,
                ssh_password,
                verify_ssl,
                monitor_hours,
                sample_interval_minutes,
                quiet,
            ): server
            for server in servers
        }
        
        for future in concurrent.futures.as_completed(future_to_server):
            result = future.result()
            results.append(result)
            
            if not quiet:
                if result['success']:
                    click.echo(f"[{result['name']}] ✓ Complete", err=True)
                else:
                    click.echo(f"[{result['name']}] ✗ Failed: {result['error']}", err=True)
    
    return results


def format_multi_server_output(results: List[Dict], output_format: str = "text") -> str:
    """
    Format multi-server results for display.
    
    Args:
        results: List of server results
        output_format: "text" or "json"
        
    Returns:
        Formatted output string
    """
    import json
    
    if output_format.lower() == "json":
        return json.dumps(results, indent=2)
    
    # Text format
    lines = ["=== Multi-Server Power Monitoring ===\n"]
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    lines.append(f"Total: {len(results)} | Success: {len(successful)} | Failed: {len(failed)}\n")
    
    if failed:
        lines.append("Failed Servers:")
        for r in failed:
            lines.append(f"  {r['name']} ({r['ip']}): {r['error']}")
        lines.append("")
    
    for result in successful:
        metrics = result['metrics']
        lines.append(f"--- {result['name']} ({result['ip']}) ---")
        
        # Check if monitoring mode or single reading
        if 'system_average_watts' in metrics:
            # Monitoring mode
            duration_str = format_duration(metrics['monitoring_duration_hours'])
            lines.append(f"  Duration: {duration_str} ({metrics['sample_count']} samples)")
            lines.append(f"  System Average: {metrics['system_average_watts']} W")
            lines.append(f"  System Range: {metrics['system_min_watts']} - {metrics['system_max_watts']} W")
            
            lines.append("  Power Supplies:")
            for psu in metrics.get('power_supplies', []):
                lines.append(f"    {psu['name']}: {psu.get('state')} - {psu.get('health')}")
                if psu.get('average_output_watts') is not None:
                    lines.append(f"      Avg Output: {psu['average_output_watts']} W")
        else:
            # Single reading
            avg_watts = metrics.get('average_watts') or metrics.get('current_watts')
            lines.append(f"  Power: {avg_watts} W")
            
            if metrics.get('redundancy'):
                red = metrics['redundancy']
                lines.append(f"  Redundancy: {red['mode']}")
            
            lines.append("  Power Supplies:")
            for psu in metrics.get('power_supplies', []):
                lines.append(f"    {psu['name']}: {psu.get('state')} - {psu.get('health')}")
                if psu.get('output_watts') is not None:
                    lines.append(f"      Output: {psu['output_watts']} W")
        
        lines.append("")
    
    return "\n".join(lines)
