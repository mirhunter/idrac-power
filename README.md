# iDRAC Power Monitor

CLI tool to connect to Dell iDRAC and retrieve current power usage metrics. Supports single-server instant readings, continuous monitoring with averaging, and parallel multi-server monitoring.

## Installation

### Production Installation (Recommended)

**Using pip in a virtual environment (isolated, recommended):**
```bash
# Create virtual environment
python3 -m venv idrac-env

# Activate virtual environment
source idrac-env/bin/activate  # On Linux/macOS
# or
idrac-env\Scripts\activate     # On Windows

# Install from source
pip install .

# Tool is now available while venv is active
idrac-power --help

# To use without activating venv each time, create a symlink:
sudo ln -s $(pwd)/idrac-env/bin/idrac-power /usr/local/bin/idrac-power
```

**Installing from PyPI (once published):**
```bash
# System-wide (requires sudo, not recommended)
sudo pip install idrac-power

# User installation (recommended)
pip install --user idrac-power

# In virtual environment (recommended)
python3 -m venv idrac-env
source idrac-env/bin/activate
pip install idrac-power
```

**Direct user installation from source:**
```bash
# Installs to ~/.local/bin/idrac-power
pip install --user .
```

### Development Installation

**For contributing or modifying the code:**
```bash
# Clone the repository
git clone https://github.com/yourusername/idrac-power.git
cd idrac-power

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in editable mode with development tools
pip install -e ".[dev]"

# Now you can edit source code and changes take effect immediately
# Development tools (pytest, black, ruff, mypy) are also installed
```

## Usage

### Single Server Monitoring

```bash
# Single instant reading (1-min average from iDRAC)
# Note: --no-verify-ssl is typically needed as iDRACs use self-signed certs
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl

# 24-hour monitoring with default 5-minute samples
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl --monitor 24h

# Custom duration and sample interval (human-friendly time formats)
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl \
  --monitor 12h --sample-interval 10m  # 12 hours, sample every 10 minutes

# Short monitoring examples
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl --monitor 5m
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl --monitor 30m --sample-interval 1m
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl --monitor 1d --sample-interval 1h

# JSON output (instead of text)
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl \
  --monitor 24h --format json

# Save report to file (auto-adds .txt or .json extension)
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl \
  --monitor 24h --output report
# Creates: report.txt

# JSON report to file
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl \
  --monitor 24h --format json --output daily-power-report
# Creates: daily-power-report.json

# Quiet mode (suppress progress messages, only show final report)
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl \
  --monitor 24h --quiet

# Perfect for cron jobs or automation
idrac-power --host 192.0.2.10 --username root --password calvin --no-verify-ssl \
  --monitor 24h --format json --output report --quiet
```

### Multi-Server Monitoring

Monitor multiple servers in parallel from a CSV file:

```bash
# Basic multi-server monitoring (instant readings)
idrac-power --servers-file servers.csv --no-verify-ssl

# Multi-server with 24-hour monitoring
idrac-power --servers-file servers.csv --no-verify-ssl --monitor 24h

# Multi-server with custom sample interval
idrac-power --servers-file servers.csv --no-verify-ssl --monitor 24h --sample-interval 15m

# JSON output for all servers
idrac-power --servers-file servers.csv --no-verify-ssl --format json

# Control parallelism (default: 5 parallel connections)
idrac-power --servers-file servers.csv --no-verify-ssl --max-workers 10

# Save multi-server report to file
idrac-power --servers-file servers.csv --no-verify-ssl --monitor 24h --output report
# Creates: report.txt

# JSON report for automation/NetBox integration
idrac-power --servers-file servers.csv --no-verify-ssl --monitor 24h \
  --format json --output power-data

# Quiet mode for cron jobs (only errors and final report)
idrac-power --servers-file servers.csv --no-verify-ssl --monitor 24h \
  --format json --output daily-report --quiet
```

### Environment Variables

```bash
# Use environment variables for credentials
export IDRAC_HOST=192.0.2.10
export IDRAC_USERNAME=root
export IDRAC_PASSWORD=calvin
idrac-power --monitor 24h

# Use jumphost for SSH tunneling
export IDRAC_JUMPHOST=jumphost.example.com
export IDRAC_JUMPHOST_USER=admin
idrac-power --host 192.0.2.10 --username root --password calvin
```

### Network Options

```bash
# Direct access (default - no SSH tunnel)
idrac-power --host 192.0.2.10 --username root --password calvin

# Through SSH jumphost
idrac-power --host 192.0.2.10 --username root --password calvin \
  --jumphost jumphost.example.com

# Jumphost with specific SSH key
idrac-power --host 192.0.2.10 --username root --password calvin \
  --jumphost jumphost.example.com --ssh-key ~/.ssh/id_rsa_custom
# Jumphost with custom SSH settings
idrac-power --host 192.0.2.10 --username root --password calvin \
  --jumphost jumphost.example.com --jumphost-user admin --ssh-key ~/.ssh/jumphost_key
```

## Command-Line Options

### Connection Options
- `--host` - iDRAC IP address (or use `IDRAC_HOST` env var)
- `--username` - iDRAC username (or use `IDRAC_USERNAME` env var)
- `--password` - iDRAC password (or use `IDRAC_PASSWORD` env var)
- `--port` - iDRAC HTTPS port (default: 443)
- `--no-verify-ssl` - Disable SSL certificate verification (needed for self-signed certs)

### SSH Tunnel Options
- `--jumphost` - SSH jumphost server (optional, for tunneling through bastion host)
- `--jumphost-user` - SSH username for jumphost (default: current user)
- `--ssh-key` - Path to SSH private key for jumphost (auto-detected if not specified)
- `--ssh-password` - SSH password for jumphost (if not using keys)
- `--no-tunnel` - Disable SSH tunnel (for direct iDRAC access)

### Monitoring Options
- `--monitor DURATION` - Enable continuous monitoring mode
  - Format: `<number><unit>` where unit is `s` (seconds), `m` (minutes), `h` (hours), or `d` (days)
  - Examples: `5m`, `12h`, `24h`, `1d`, `30m`
- `--sample-interval INTERVAL` - How often to sample (default: 5m)
  - Same format as `--monitor`
  - Examples: `1m`, `5m`, `10m`, `1h`

### Multi-Server Options
- `--servers-file FILE` - CSV file with server list (ip,username,password,name)
- `--max-workers N` - Maximum parallel connections (default: 5)

### Output Options
- `--format FORMAT` - Output format: `text` or `json` (default: text)
- `--output FILE` - Save report to file (auto-adds .txt or .json extension)
- `--quiet` / `-q` - Suppress progress messages (only show errors and final report)

## Time Format

Duration and interval values support human-friendly formats:
- Seconds: `30s`, `90s`
- Minutes: `1m`, `5m`, `30m`
- Hours: `1h`, `12h`, `24h`
- Days: `1d`, `7d`

Examples:
- `--monitor 5m --sample-interval 30s` - Monitor for 5 minutes, sample every 30 seconds
- `--monitor 24h --sample-interval 15m` - Monitor for 24 hours, sample every 15 minutes
- `--monitor 1d --sample-interval 1h` - Monitor for 1 day, sample every hour

## Error Handling

### Network Resilience

The tool is designed to handle transient network issues during long-running monitoring sessions:

**Automatic Retry Logic:**
- Failed API calls are automatically retried up to **3 times**
- Uses **exponential backoff** (2s → 4s → 8s) between retry attempts
- Monitoring continues even if individual samples fail
- Progress messages show retry attempts and failures

**Example:**
```
[2026-02-19 14:58:32] Sample 26/1440 (1.8%) - System: 366W
Error collecting sample (attempt 1/3): Connection aborted. Retrying in 2s...
Error collecting sample (attempt 2/3): Connection aborted. Retrying in 4s...
[2026-02-19 14:58:43] Sample 27/1440 (1.9%) - System: 351W
```

This ensures that brief network hiccups or iDRAC temporary unavailability won't terminate a 24-hour monitoring run. Only if all 3 attempts fail will the sample be skipped.

## Use Cases

### UPS Sizing
Monitor power consumption over 24 hours to determine peak and average loads:
```bash
idrac-power --servers-file production-servers.csv --no-verify-ssl \
  --monitor 24h --sample-interval 5m --format json --output ups-sizing-data
```

### Quick Health Check
Get instant power readings across all servers:
```bash
idrac-power --servers-file servers.csv --no-verify-ssl
```

## Production Deployment

### Automated Monitoring (Cron)

**Daily power monitoring report:**
```bash
# Add to crontab (crontab -e)
0 0 * * * /usr/local/bin/idrac-power --servers-file /etc/idrac/servers.csv \
  --monitor 24h --sample-interval 1h --format json \
  --output /var/data/power-reports/daily-$(date +\%Y\%m\%d) --quiet
```

### Systemd Service (Long-running monitoring)

Create `/etc/systemd/system/idrac-monitor.service`:
```ini
[Unit]
Description=iDRAC Power Monitoring Service
After=network.target

[Service]
Type=simple
User=idrac-monitor
WorkingDirectory=/opt/idrac-power
ExecStart=/opt/idrac-power/venv/bin/idrac-power \
  --servers-file /etc/idrac/servers.csv \
  --monitor 24h --sample-interval 5m \
  --format json --output /var/log/idrac/power-report --quiet
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable idrac-monitor
sudo systemctl start idrac-monitor
sudo systemctl status idrac-monitor
```

### Environment Variables for Production

**Create `/etc/idrac/environment`:**
```bash
# iDRAC credentials (if using single server)
IDRAC_HOST=192.0.2.10
IDRAC_USERNAME=monitoring
IDRAC_PASSWORD=secure_password_here

# SSH jumphost configuration
IDRAC_JUMPHOST=bastion.example.com
IDRAC_JUMPHOST_USER=svc-monitor
IDRAC_JUMPHOST_SSH_KEY=/etc/idrac/ssh/jumphost_key
```

**Load in service:**
```ini
[Service]
EnvironmentFile=/etc/idrac/environment
```

### Security Best Practices

1. **Store credentials securely:**
   ```bash
   # Use restrictive permissions
   chmod 600 /etc/idrac/servers.csv
   chown idrac-monitor:idrac-monitor /etc/idrac/servers.csv
   ```

2. **Use dedicated service account:**
   ```bash
   sudo useradd -r -s /bin/false idrac-monitor
   ```

3. **Use SSH keys instead of passwords:**
   ```bash
   # Generate key for jumphost
   ssh-keygen -t ed25519 -f /etc/idrac/ssh/jumphost_key -N ""
   # Add public key to jumphost authorized_keys
   ```

4. **Rotate credentials regularly:**
   - Update CSV file with new passwords
   - Reload service: `sudo systemctl restart idrac-monitor`

### Docker Deployment

**Create `Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy configuration
COPY servers.csv /etc/idrac/servers.csv

# Run as non-root
RUN useradd -r -u 1000 idrac && \
    mkdir -p /home/idrac/.ssh && \
    chown -R idrac:idrac /home/idrac
USER idrac

ENTRYPOINT ["idrac-power"]
CMD ["--servers-file", "/etc/idrac/servers.csv", "--format", "json"]
```

**Run container (direct access - no jumphost):**
```bash
docker build -t idrac-power .
docker run -v /path/to/servers.csv:/etc/idrac/servers.csv:ro \
  -v /path/to/output:/output \
  idrac-power --servers-file /etc/idrac/servers.csv \
  --monitor 24h --output /output/report --quiet
```

**Run container with jumphost (SSH key required):**
```bash
# Mount SSH key as read-only
docker run \
  -v /path/to/servers.csv:/etc/idrac/servers.csv:ro \
  -v /path/to/output:/output \
  -v ~/.ssh/jumphost_key:/home/idrac/.ssh/jumphost_key:ro \
  idrac-power \
    --servers-file /etc/idrac/servers.csv \
    --jumphost bastion.example.com \
    --ssh-key /home/idrac/.ssh/jumphost_key \
    --monitor 24h --output /output/report --quiet
```

**Run container with SSH agent forwarding:**
```bash
# Forward your host SSH agent to container
docker run \
  -v /path/to/servers.csv:/etc/idrac/servers.csv:ro \
  -v /path/to/output:/output \
  -v $SSH_AUTH_SOCK:/ssh-agent \
  -e SSH_AUTH_SOCK=/ssh-agent \
  idrac-power \
    --servers-file /etc/idrac/servers.csv \
    --jumphost bastion.example.com \
    --monitor 24h --output /output/report --quiet
```

**Using per-server jumphosts in CSV:**
```bash
# CSV contains jumphost columns with SSH key paths
# Mount all necessary keys
docker run \
  -v /path/to/servers.csv:/etc/idrac/servers.csv:ro \
  -v /path/to/output:/output \
  -v ~/.ssh/dc1_key:/home/idrac/.ssh/dc1_key:ro \
  -v ~/.ssh/dc2_key:/home/idrac/.ssh/dc2_key:ro \
  idrac-power \
    --servers-file /etc/idrac/servers.csv \
    --monitor 24h --output /output/report --quiet
```

**Docker Compose example with jumphost:**
```yaml
version: '3.8'

services:
  idrac-monitor:
    build: .
    volumes:
      - ./servers.csv:/etc/idrac/servers.csv:ro
      - ./output:/output
      - ~/.ssh/jumphost_key:/home/idrac/.ssh/jumphost_key:ro
    command:
      - --servers-file
      - /etc/idrac/servers.csv
      - --jumphost
      - bastion.example.com
      - --ssh-key
      - /home/idrac/.ssh/jumphost_key
      - --monitor
      - 24h
      - --output
      - /output/report
      - --quiet
    restart: unless-stopped
```

> **Security Note:** When mounting SSH keys into containers, always use `:ro` (read-only) to prevent the container from modifying your keys.

## Development

### Setup

```bash
# Install in development mode
pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run a specific test
pytest tests/test_client.py::test_connection
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Configuration

### Server List CSV Format

For multi-server monitoring, create a CSV file with the following format:

**Basic format (required columns):**
```csv
ip,username,password,name
192.0.2.10,root,pass1,server1
192.0.2.11,root,pass2,server2
192.0.2.12,root,pass3,server3
```

**Required columns:** `ip`, `username`, `password`  
**Optional columns:** `name`, `port`, `jumphost`, `jumphost_user`, `jumphost_ssh_key`, `jumphost_ssh_password`

**With custom ports:**
```csv
ip,username,password,name,port
192.0.2.10,root,pass1,server1,443
192.0.2.11,root,pass2,server2,8443
```

**With per-server jumphosts:**
```csv
ip,username,password,name,jumphost,jumphost_user
192.0.2.10,root,pass1,server1,jump1.example.com,admin
192.0.2.11,root,pass2,server2,jump2.example.com,admin
192.0.2.12,root,pass3,server3,,,
```

**Mixed configuration (some servers with jumphost, some direct):**
```csv
ip,username,password,name,jumphost,jumphost_user,jumphost_ssh_key
192.0.2.10,root,pass1,datacenter1-srv1,jump.dc1.example.com,admin,~/.ssh/dc1_key
192.0.2.11,root,pass2,datacenter1-srv2,jump.dc1.example.com,admin,~/.ssh/dc1_key
192.0.2.20,root,pass3,datacenter2-srv1,,,
192.0.2.21,root,pass4,datacenter2-srv2,,,
```

> **Note:** Per-server jumphost settings override global `--jumphost` CLI options. Leave jumphost columns empty for direct access to specific servers.

### Environment Variables

The tool accepts credentials and configuration via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `IDRAC_HOST` | iDRAC IP address | - |
| `IDRAC_USERNAME` | iDRAC username | - |
| `IDRAC_PASSWORD` | iDRAC password | - |
| `IDRAC_JUMPHOST` | SSH jumphost server | - |
| `IDRAC_JUMPHOST_USER` | SSH username for jumphost | Current user |
| `IDRAC_JUMPHOST_SSH_KEY` | Path to SSH private key for jumphost | Auto-detected |
| `IDRAC_JUMPHOST_SSH_PASSWORD` | SSH password for jumphost | - |

### SSH Tunnel Support

**SSH tunneling is optional** and only used when explicitly configured via `--jumphost` flag or `IDRAC_JUMPHOST` environment variable.

**When using a jumphost**, the tool automatically:
1. Detects your SSH keys (checks SSH agent and `~/.ssh/id_*`)
2. Establishes SSH connection to the specified jumphost
3. Creates a local port forward to the iDRAC
4. Connects to iDRAC through the tunnel
5. Cleans up the tunnel on exit

#### SSH Authentication Priority

When connecting to a jumphost, authentication methods are tried in this order:

1. **SSH Key** (if `--ssh-key` or `jumphost_ssh_key` specified) - **Preferred** ✅
2. **Password** (if `--ssh-password` or `jumphost_ssh_password` specified and no key)
3. **Auto-detect** (if neither specified) - Uses SSH agent and `~/.ssh/id_*`

> **Note:** If both SSH key and password are provided, the **SSH key takes priority** and the password is ignored. This follows [SSH best practices](https://www.ssh.com/academy/ssh/public-key-authentication) where key-based authentication is preferred over password authentication for security.

**Example CSV with mixed authentication:**
```csv
ip,username,password,jumphost,jumphost_user,jumphost_ssh_key
192.0.2.10,root,pass1,jump1.example.com,admin,~/.ssh/dc1_key
192.0.2.11,root,pass2,jump2.example.com,admin,
192.0.2.12,root,pass3,,,
```
- Server 1: Uses specified SSH key `~/.ssh/dc1_key`
- Server 2: Uses auto-detected keys (SSH agent or `~/.ssh/id_*`)
- Server 3: Direct access (no jumphost)

#### Usage Examples

**Direct access (default):**
```bash
idrac-power --host 192.0.2.10 --username root --password calvin
```

**Through jumphost:**
```bash
idrac-power --host 192.0.2.10 --username root --password calvin \
  --jumphost jumphost.example.com
```

**Jumphost with specific SSH key:**
```bash
idrac-power --host 192.0.2.10 --username root --password calvin \
  --jumphost jumphost.example.com --ssh-key ~/.ssh/jumphost_key
```

**Per-server jumphosts (multi-server mode):**
Configure jumphosts per-server in the CSV file. See [Server List CSV Format](#server-list-csv-format) for details.

## Output Examples

### Text Output (Default)

```
=== Power Metrics ===
System Power: 352 W (1-min average)
System Power Limit: 1050 W

Power Redundancy: FullyRedundant (N+m mode)

Power Supply 1:
  Status: Enabled - OK
  Capacity: 1050 W
  Output Power: 162 W
  Input Power: 177 W
  Efficiency: 92%

Power Supply 2:
  Status: Enabled - OK
  Capacity: 1050 W
  Output Power: N/A (standby)
  Input Power: 5 W
  Efficiency: N/A
```

### JSON Output

```json
{
  "timestamp": "2026-02-19T12:34:56",
  "system": {
    "power_watts": 352,
    "power_limit_watts": 1050
  },
  "redundancy": {
    "status": "FullyRedundant",
    "mode": "N+m"
  },
  "power_supplies": [
    {
      "name": "PS1",
      "status": "Enabled",
      "health": "OK",
      "capacity_watts": 1050,
      "output_watts": 162,
      "input_watts": 177,
      "efficiency_percent": 92.0
    }
  ]
}
```

### Multi-Server Text Output

```
=== Multi-Server Power Monitoring ===

Total: 3 | Success: 3 | Failed: 0

[server1] 192.0.2.10
  System: 352 W | PS1: 162W/177W (92%) | PS2: 162W/176W (92%)

[server2] 192.0.2.11
  System: 298 W | PS1: 145W/158W (92%) | PS2: N/A/5W (standby)

[server3] 192.0.2.12
  System: 415 W | PS1: 201W/219W (92%) | PS2: 201W/218W (92%)
```

## Requirements

- Python 3.8+
- Network access to iDRAC interface
- Valid iDRAC credentials

## Acknowledgments

This project was developed with assistance from GitHub Copilot CLI, an AI pair programming tool. The initial codebase, architecture, and documentation were collaboratively created through an interactive development session.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Allen St. John - [astjohn+github@dvce.us](mailto:astjohn+github@dvce.us)
