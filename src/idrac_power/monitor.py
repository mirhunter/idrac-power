"""Continuous monitoring and averaging of power metrics."""

import time
import signal
import sys
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from statistics import mean

import click

from .client import IDRACClient
from .power import get_power_metrics


class PowerMonitor:
    """Monitors and averages power metrics over time."""
    
    def __init__(
        self,
        client: IDRACClient,
        duration_hours: float = 24.0,
        sample_interval_minutes: int = 5,
        quiet: bool = False,
    ) -> None:
        """
        Initialize power monitor.
        
        Args:
            client: Authenticated IDRACClient instance
            duration_hours: How long to monitor (hours)
            sample_interval_minutes: Time between samples (minutes)
            quiet: Suppress progress messages
        """
        self.client = client
        self.duration_hours = duration_hours
        self.sample_interval_minutes = sample_interval_minutes
        self.quiet = quiet
        self.samples: List[Dict] = []
        self.interrupted = False
        
        # Set up signal handler only if we're in the main thread
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle CTRL+C gracefully."""
        self.interrupted = True
        # Don't print here - let the main loop handle it
    
    def run(self) -> Dict:
        """
        Run monitoring loop and collect samples.
        
        Returns:
            Dictionary with averaged metrics
        """
        end_time = datetime.now() + timedelta(hours=self.duration_hours)
        sample_count = 0
        total_samples = int((self.duration_hours * 60) / self.sample_interval_minutes)
        
        if not self.quiet:
            click.echo(f"Starting {self.duration_hours}h monitoring (sampling every {self.sample_interval_minutes} min)", err=True)
            click.echo(f"Expected {total_samples} samples. Press CTRL+C to stop early.\n", err=True)
        
        while datetime.now() < end_time and not self.interrupted:
            try:
                # Get current metrics with retry logic
                metrics = None
                max_retries = 3
                retry_delay = 2  # Start with 2 seconds
                
                for attempt in range(max_retries):
                    try:
                        metrics = get_power_metrics(self.client)
                        break  # Success, exit retry loop
                    except Exception as e:
                        if attempt < max_retries - 1:
                            if not self.quiet:
                                click.echo(
                                    f"Error collecting sample (attempt {attempt + 1}/{max_retries}): {e}. "
                                    f"Retrying in {retry_delay}s...",
                                    err=True
                                )
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            # All retries failed
                            if not self.quiet:
                                click.echo(f"Error collecting sample after {max_retries} attempts: {e}", err=True)
                            raise  # Re-raise to outer exception handler
                
                if metrics is None:
                    # Shouldn't happen, but skip this sample if it does
                    continue
                
                sample_time = datetime.now()
                
                # Store sample
                sample = {
                    "timestamp": sample_time,
                    "current_watts": metrics.get("current_watts"),
                    "power_supplies": metrics.get("power_supplies", []),
                }
                self.samples.append(sample)
                sample_count += 1
                
                # Show progress
                elapsed = timedelta(hours=self.duration_hours) - (end_time - datetime.now())
                remaining = end_time - datetime.now()
                progress = (sample_count / total_samples) * 100 if total_samples > 0 else 0
                
                if not self.quiet:
                    click.echo(
                        f"[{sample_time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"Sample {sample_count}/{total_samples} ({progress:.1f}%) - "
                        f"System: {metrics.get('current_watts')}W - "
                        f"Elapsed: {str(elapsed).split('.')[0]} - "
                        f"Remaining: {str(remaining).split('.')[0]}",
                        err=True
                    )
                
                # Check if we need another sample
                next_sample_time = sample_time + timedelta(minutes=self.sample_interval_minutes)
                if next_sample_time >= end_time:
                    # This was the last sample, no need to sleep
                    break
                
                # Sleep until next sample
                if not self.interrupted:
                    # Sleep in smaller chunks to be more responsive to CTRL+C (only in main thread)
                    sleep_seconds = self.sample_interval_minutes * 60
                    sleep_start = time.time()
                    
                    # In threads, just sleep the full duration
                    if threading.current_thread() is not threading.main_thread():
                        time.sleep(sleep_seconds)
                    else:
                        # In main thread, sleep in chunks for CTRL+C responsiveness
                        while (time.time() - sleep_start) < sleep_seconds and not self.interrupted:
                            try:
                                # Sleep in 1-second chunks for responsiveness
                                remaining_sleep = sleep_seconds - (time.time() - sleep_start)
                                time.sleep(min(1, remaining_sleep))
                            except KeyboardInterrupt:
                                self.interrupted = True
                                click.echo("\n\nMonitoring interrupted.", err=True)
                                break
                    
            except KeyboardInterrupt:
                # CTRL+C during API call
                self.interrupted = True
                click.echo("\n\nMonitoring interrupted.", err=True)
                break
            except Exception as e:
                if not self.quiet:
                    click.echo(f"Error collecting sample: {e}", err=True)
                time.sleep(self.sample_interval_minutes * 60)
        
        if not self.quiet:
            click.echo(f"\nMonitoring complete. Collected {sample_count} samples.\n", err=True)
        
        # If interrupted, ask if user wants to see results (only in main thread)
        if self.interrupted and threading.current_thread() is threading.main_thread():
            if sample_count == 0:
                click.echo("No samples collected. Exiting.", err=True)
                sys.exit(0)
            
            show_results = click.confirm(
                f"Calculate averages from {sample_count} sample(s)?",
                default=True
            )
            if not show_results:
                click.echo("Exiting without calculating averages.", err=True)
                sys.exit(0)
        
        return self._calculate_averages()
    
    def _calculate_averages(self) -> Dict:
        """
        Calculate averages from collected samples.
        
        Returns:
            Dictionary with averaged metrics
        """
        if not self.samples:
            raise ValueError("No samples collected")
        
        # Calculate system-level average
        system_watts = [s["current_watts"] for s in self.samples if s["current_watts"] is not None]
        
        # Calculate per-PSU averages
        psu_data = {}
        for sample in self.samples:
            for psu in sample.get("power_supplies", []):
                psu_name = psu.get("name")
                if psu_name not in psu_data:
                    psu_data[psu_name] = {
                        "output_watts": [],
                        "input_watts": [],
                        "efficiency": [],
                        "capacity_watts": psu.get("capacity_watts"),
                        "last_state": psu.get("state"),
                        "last_health": psu.get("health"),
                    }
                
                if psu.get("output_watts") is not None:
                    psu_data[psu_name]["output_watts"].append(psu["output_watts"])
                if psu.get("input_watts") is not None:
                    psu_data[psu_name]["input_watts"].append(psu["input_watts"])
                if psu.get("efficiency_percent") is not None:
                    psu_data[psu_name]["efficiency"].append(psu["efficiency_percent"])
        
        # Calculate averages
        averages = {
            "monitoring_duration_hours": self.duration_hours,
            "sample_count": len(self.samples),
            "sample_interval_minutes": self.sample_interval_minutes,
            "start_time": self.samples[0]["timestamp"].isoformat() if self.samples else None,
            "end_time": self.samples[-1]["timestamp"].isoformat() if self.samples else None,
            "system_average_watts": int(mean(system_watts)) if system_watts else None,
            "system_min_watts": int(min(system_watts)) if system_watts else None,
            "system_max_watts": int(max(system_watts)) if system_watts else None,
            "power_supplies": []
        }
        
        for psu_name, data in psu_data.items():
            psu_avg = {
                "name": psu_name,
                "state": data["last_state"],
                "health": data["last_health"],
                "capacity_watts": data["capacity_watts"],
            }
            
            if data["output_watts"]:
                psu_avg["average_output_watts"] = int(mean(data["output_watts"]))
                psu_avg["min_output_watts"] = int(min(data["output_watts"]))
                psu_avg["max_output_watts"] = int(max(data["output_watts"]))
            
            if data["input_watts"]:
                psu_avg["average_input_watts"] = int(mean(data["input_watts"]))
                psu_avg["min_input_watts"] = int(min(data["input_watts"]))
                psu_avg["max_input_watts"] = int(max(data["input_watts"]))
            
            if data["efficiency"]:
                psu_avg["average_efficiency_percent"] = round(mean(data["efficiency"]), 1)
            
            averages["power_supplies"].append(psu_avg)
        
        return averages
