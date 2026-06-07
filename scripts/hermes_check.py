#!/usr/bin/env python3
"""Zabbix external check: query a Hermes profile's API server.

Usage:
    hermes_check.py health <profile> [host] [port] [key]
    hermes_check.py tokens <profile> [host] [port] [key]
    hermes_check.py profiles                   # LLD: discover profiles

Each command can receive connection details as positional args (e.g. from
Zabbix template macros) OR fall back to reading the profile's .env.

Requires:
    - HERMES_HOME env var, or defaults to /root/.hermes
    - The target Hermes profile must have API_SERVER_ENABLED=true
"""

import json
import os
import sys
import time as _time
import urllib.request
from pathlib import Path
from urllib.error import HTTPError, URLError


def _hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()


def _read_profile_env(profile: str) -> dict:
    """Read a Hermes profile's .env file."""
    h = _hermes_home()
    if profile == "default":
        env_path = h / ".env"
    else:
        env_path = h / "profiles" / profile / ".env"

    vars_ = {}
    if env_path.is_file():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                vars_[k.strip()] = v.strip()
    return vars_


def _get_profile_connection(profile: str) -> tuple:
    """Return (host, port, api_key) for a profile, or raise."""
    env = _read_profile_env(profile)
    enabled = env.get("API_SERVER_ENABLED", "").lower()
    if enabled not in ("true", "1", "yes"):
        raise RuntimeError(
            f"Profile '{profile}' does not have API_SERVER_ENABLED=true. "
            f"Add to {_hermes_home() if profile == 'default' else _hermes_home() / 'profiles' / profile / '.env'}"
        )
    host = env.get("API_SERVER_HOST", "127.0.0.1")
    port = env.get("API_SERVER_PORT", "8642")
    key = env.get("API_SERVER_KEY", "")
    return host, port, key


def _api_get(host: str, port: str, path: str, api_key: str = "") -> dict:
    """GET a JSON endpoint from the Hermes API server."""
    url = f"http://{host}:{port}{path}"
    req = urllib.request.Request(url)
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}", "detail": body[:500]}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def cmd_health(profile: str, host: str = None, port: str = None,
               key: str = None) -> str:
    """Fetch /health/detailed and return gateway metrics.

    If host and port are given, use them directly (macro-based).
    Otherwise fall back to profile .env.
    """
    if host and port:
        data = _api_get(host, port, "/health/detailed", key or "")
    else:
        host, port, key = _get_profile_connection(profile)
        data = _api_get(host, port, "/health/detailed", key)

    if "error" in data:
        return json.dumps(data)

    return json.dumps({
        "gateway_up": 1 if data.get("gateway_state") == "running" else 0,
        "gateway_state": data.get("gateway_state", "unknown"),
        "active_agents": data.get("active_agents", 0),
        "platforms_connected": sum(
            1 for p in data.get("platforms", {}).values()
            if p.get("state") == "connected"
        ),
        "platforms_total": len(data.get("platforms", {})),
        "pid": data.get("pid", 0),
    })


def cmd_tokens(profile: str, host: str = None, port: str = None,
               key: str = None) -> str:
    """Fetch /api/sessions and aggregate token metrics.

    If host and port are given, use them directly (macro-based).
    Otherwise fall back to profile .env.
    """
    if host and port:
        data = _api_get(host, port, "/api/sessions?limit=200", key or "")
    else:
        host, port, key = _get_profile_connection(profile)
        data = _api_get(host, port, "/api/sessions?limit=200", key)

    if "error" in data:
        return json.dumps(data)

    sessions = data.get("data", [])
    active = [s for s in sessions if s.get("ended_at") is None]
    week_ago = _time.time() - 604800

    return json.dumps({
        "active_sessions": len(active),
        "total_sessions": len(sessions),
        "total_input_tokens": sum(s.get("input_tokens") or 0 for s in sessions),
        "total_output_tokens": sum(s.get("output_tokens") or 0 for s in sessions),
        "total_cache_read_tokens": sum(s.get("cache_read_tokens") or 0 for s in sessions),
        "total_tool_calls": sum(s.get("tool_call_count") or 0 for s in sessions),
        "total_messages": sum(s.get("message_count") or 0 for s in sessions),
        "sessions_7d": sum(
            1 for s in sessions if (s.get("started_at") or 0) > week_ago
        ),
        "tokens_7d": sum(
            (s.get("input_tokens") or 0) + (s.get("output_tokens") or 0)
            for s in sessions if (s.get("started_at") or 0) > week_ago
        ),
        "last_active_ts": max(
            (s.get("last_active") or 0) for s in sessions
        ) if sessions else 0,
    })


def cmd_profiles() -> str:
    """Discover profiles with API servers — Zabbix LLD output."""
    h = _hermes_home()
    profiles = []

    def _check(env_path: Path, name: str):
        if not env_path.is_file():
            return
        vars_ = {}
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                vars_[k.strip()] = v.strip()
        if vars_.get("API_SERVER_ENABLED", "").lower() in ("true", "1", "yes"):
            profiles.append({
                "{#PROFILE}": name,
            })

    _check(h / ".env", "default")
    profiles_dir = h / "profiles"
    if profiles_dir.is_dir():
        for pdir in sorted(profiles_dir.iterdir()):
            if pdir.is_dir():
                _check(pdir / ".env", pdir.name)

    return json.dumps({"data": profiles}, indent=2)


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    command = sys.argv[1]

    if command == "profiles":
        print(cmd_profiles())
        return

    if len(sys.argv) < 3:
        print(f"Usage: hermes_check.py {command} <profile>", file=sys.stderr)
        sys.exit(1)

    profile = sys.argv[2]
    host = sys.argv[3] if len(sys.argv) > 3 else None
    port = sys.argv[4] if len(sys.argv) > 4 else None
    key = sys.argv[5] if len(sys.argv) > 5 else ""

    try:
        if command == "health":
            print(cmd_health(profile, host, port, key))
        elif command == "tokens":
            print(cmd_tokens(profile, host, port, key))
        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            sys.exit(1)
    except RuntimeError as e:
        # Profile doesn't have API_SERVER_ENABLED
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
