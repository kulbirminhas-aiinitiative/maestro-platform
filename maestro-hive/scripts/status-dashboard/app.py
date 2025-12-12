#!/usr/bin/env python3
"""
Web-Based Service Status Dashboard
MD-2033: Part of EPIC MD-1979 - Service Resilience & Operational Hardening

A lightweight web dashboard for viewing service status across environments
without requiring SSH access.
"""

import os
import json
import time
import subprocess
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from functools import wraps

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'maestro-status-dashboard-secret-2024')
CORS(app)

# Configuration
# MD-3054 FIX: Configurable PM2 service filter prefixes
# Can be overridden via PM2_SERVICE_PREFIXES environment variable (comma-separated)
DEFAULT_PM2_PREFIXES = ['maestro', 'dev-', 'sandbox-', 'demo-', 'gateway', 'quality-fabric', 'llm-', 'rag-']
PM2_SERVICE_PREFIXES = os.environ.get('PM2_SERVICE_PREFIXES', '').split(',') if os.environ.get('PM2_SERVICE_PREFIXES') else DEFAULT_PM2_PREFIXES

# If empty (shows all) is explicitly configured
if os.environ.get('PM2_SHOW_ALL', '').lower() == 'true':
    PM2_SERVICE_PREFIXES = []  # Empty list = show all

ENVIRONMENTS = {
    'development': {
        'name': 'Development',
        'host': 'localhost',
        'health_port': 4100,
        'pm2_enabled': True,
    },
    'sandbox': {
        'name': 'Sandbox',
        'host': 'localhost',
        'health_port': 14100,
        'pm2_enabled': True,
    },
    'demo': {
        'name': 'Demo',
        'host': 'localhost',
        'health_port': 4100,
        'pm2_enabled': True,
    },
}

# Simple auth (in production, use proper auth)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'maestro_status_2024')

# Health check history storage
health_history: Dict[str, List[dict]] = {env: [] for env in ENVIRONMENTS}
MAX_HISTORY_ENTRIES = 100

# Incident timeline
incidents: List[dict] = []
MAX_INCIDENTS = 50


@dataclass
class ServiceStatus:
    name: str
    status: str  # 'online', 'offline', 'degraded'
    uptime: Optional[str] = None
    memory: Optional[str] = None
    cpu: Optional[str] = None
    restarts: Optional[int] = None
    pid: Optional[int] = None
    last_check: Optional[str] = None


@dataclass
class EnvironmentStatus:
    name: str
    environment_key: str
    overall_status: str  # 'healthy', 'degraded', 'down'
    services: List[ServiceStatus]
    health_endpoint: Optional[dict] = None
    last_updated: Optional[str] = None


def login_required(f):
    """Simple authentication decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def check_health_endpoint(host: str, port: int, timeout: int = 5) -> dict:
    """Check a health endpoint and return status."""
    try:
        url = f'http://{host}:{port}/health'
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            try:
                data = response.json()
                return {
                    'status': 'healthy',
                    'response': data,
                    'response_time_ms': int(response.elapsed.total_seconds() * 1000)
                }
            except:
                return {
                    'status': 'healthy',
                    'response': response.text[:200],
                    'response_time_ms': int(response.elapsed.total_seconds() * 1000)
                }
        else:
            return {
                'status': 'degraded',
                'error': f'HTTP {response.status_code}',
                'response_time_ms': int(response.elapsed.total_seconds() * 1000)
            }
    except requests.exceptions.Timeout:
        return {'status': 'timeout', 'error': 'Request timed out'}
    except requests.exceptions.ConnectionError:
        return {'status': 'down', 'error': 'Connection refused'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def get_pm2_status(env_key: str = None) -> List[ServiceStatus]:
    """Get PM2 process status, optionally filtered by environment.

    Args:
        env_key: Environment key to filter services (e.g., 'sandbox', 'development', 'demo')
                 If provided, only services matching the environment prefix are returned.
    """
    services = []

    # MD-3090 FIX: Environment-specific service prefix mapping
    # Each environment should only show its own services
    ENV_SERVICE_PREFIXES = {
        'development': ['dev-', 'development-'],
        'sandbox': ['sandbox-'],
        'demo': ['demo-', 'maestro-'],  # demo uses maestro- prefix or demo-
    }

    # Get the prefixes for this environment
    env_prefixes = ENV_SERVICE_PREFIXES.get(env_key, []) if env_key else []

    try:
        result = subprocess.run(
            ['pm2', 'jlist'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            pm2_list = json.loads(result.stdout)
            for proc in pm2_list:
                name = proc.get('name', '')

                # MD-3090 FIX: Filter by environment-specific prefix
                # If env_key is provided, only show services for that environment
                if env_prefixes:
                    if not any(name.startswith(prefix) for prefix in env_prefixes):
                        continue
                else:
                    # Fallback to global prefix filter if no env_key specified
                    if PM2_SERVICE_PREFIXES and not any(name.startswith(prefix) for prefix in PM2_SERVICE_PREFIXES):
                        continue

                pm2_env = proc.get('pm2_env', {})
                monit = proc.get('monit', {})

                status = 'online' if pm2_env.get('status') == 'online' else 'offline'
                uptime_ms = pm2_env.get('pm_uptime', 0)
                uptime = format_uptime(uptime_ms) if uptime_ms else 'N/A'

                services.append(ServiceStatus(
                    name=name,
                    status=status,
                    uptime=uptime,
                    memory=format_bytes(monit.get('memory', 0)),
                    cpu=f"{monit.get('cpu', 0):.1f}%",
                    restarts=pm2_env.get('restart_time', 0),
                    pid=proc.get('pid', None),
                    last_check=datetime.now().isoformat()
                ))
    except subprocess.TimeoutExpired:
        services.append(ServiceStatus(
            name='PM2',
            status='timeout',
            last_check=datetime.now().isoformat()
        ))
    except FileNotFoundError:
        services.append(ServiceStatus(
            name='PM2',
            status='not_installed',
            last_check=datetime.now().isoformat()
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name='PM2',
            status='error',
            last_check=datetime.now().isoformat()
        ))

    return services


def format_uptime(uptime_ms: int) -> str:
    """Format uptime in milliseconds to human readable string."""
    if not uptime_ms:
        return 'N/A'

    now = datetime.now()
    uptime_start = datetime.fromtimestamp(uptime_ms / 1000)
    delta = now - uptime_start

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f'{days}d {hours}h'
    elif hours > 0:
        return f'{hours}h {minutes}m'
    else:
        return f'{minutes}m {seconds}s'


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string."""
    if bytes_val == 0:
        return '0 B'

    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f'{bytes_val:.1f} {unit}'
        bytes_val /= 1024
    return f'{bytes_val:.1f} TB'


def get_environment_status(env_key: str) -> EnvironmentStatus:
    """Get full status for an environment."""
    config = ENVIRONMENTS.get(env_key, {})

    # Get health endpoint status
    health_status = check_health_endpoint(
        config.get('host', 'localhost'),
        config.get('health_port', 4100)
    )

    # Get PM2 services if enabled - MD-3090 FIX: pass env_key for filtering
    services = []
    if config.get('pm2_enabled', False):
        services = get_pm2_status(env_key)

    # Determine overall status
    if health_status['status'] == 'healthy' and all(s.status == 'online' for s in services):
        overall = 'healthy'
    elif health_status['status'] == 'down':
        overall = 'down'
    else:
        overall = 'degraded'

    # Store in history
    history_entry = {
        'timestamp': datetime.now().isoformat(),
        'status': overall,
        'health': health_status['status'],
        'services_online': sum(1 for s in services if s.status == 'online'),
        'services_total': len(services)
    }
    health_history[env_key].append(history_entry)
    if len(health_history[env_key]) > MAX_HISTORY_ENTRIES:
        health_history[env_key] = health_history[env_key][-MAX_HISTORY_ENTRIES:]

    # Record incident if status changed
    if len(health_history[env_key]) >= 2:
        prev = health_history[env_key][-2]['status']
        curr = overall
        if prev != curr:
            record_incident(env_key, prev, curr)

    return EnvironmentStatus(
        name=config.get('name', env_key),
        environment_key=env_key,
        overall_status=overall,
        services=[asdict(s) for s in services],
        health_endpoint=health_status,
        last_updated=datetime.now().isoformat()
    )


def record_incident(env_key: str, old_status: str, new_status: str):
    """Record a status change incident."""
    incident = {
        'id': len(incidents) + 1,
        'timestamp': datetime.now().isoformat(),
        'environment': env_key,
        'type': 'recovery' if new_status == 'healthy' else 'degradation',
        'old_status': old_status,
        'new_status': new_status,
        'message': f'{ENVIRONMENTS[env_key]["name"]} changed from {old_status} to {new_status}'
    }
    incidents.insert(0, incident)
    if len(incidents) > MAX_INCIDENTS:
        incidents.pop()


# Routes
@app.route('/')
def index():
    """Main dashboard page."""
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return render_template('index.html', environments=ENVIRONMENTS)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['authenticated'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Logout."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/status')
@login_required
def api_status():
    """Get status for all environments."""
    statuses = {}
    for env_key in ENVIRONMENTS:
        status = get_environment_status(env_key)
        statuses[env_key] = asdict(status)
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'environments': statuses
    })


@app.route('/api/status/<env_key>')
@login_required
def api_environment_status(env_key: str):
    """Get status for a specific environment."""
    if env_key not in ENVIRONMENTS:
        return jsonify({'error': 'Unknown environment'}), 404
    status = get_environment_status(env_key)
    return jsonify(asdict(status))


@app.route('/api/history/<env_key>')
@login_required
def api_history(env_key: str):
    """Get health check history for an environment."""
    if env_key not in ENVIRONMENTS:
        return jsonify({'error': 'Unknown environment'}), 404
    return jsonify({
        'environment': env_key,
        'history': health_history.get(env_key, [])
    })


@app.route('/api/incidents')
@login_required
def api_incidents():
    """Get recent incidents."""
    return jsonify({'incidents': incidents})


@app.route('/api/actions/restart/<service_name>', methods=['POST'])
@login_required
def api_restart_service(service_name: str):
    """Restart a PM2 service (admin action)."""
    try:
        result = subprocess.run(
            ['pm2', 'restart', service_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': f'Service {service_name} restarted'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health')
def health():
    """Health check endpoint for the dashboard itself."""
    return jsonify({'status': 'healthy', 'service': 'status-dashboard'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
