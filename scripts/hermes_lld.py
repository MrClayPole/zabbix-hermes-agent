#!/usr/bin/env python3
"""Zabbix Low-Level Discovery wrapper — delegates to hermes_check.py.

Usage:
    python3 hermes_lld.py

Returns JSON LLD for profiles with API_SERVER_ENABLED=true.
"""
import subprocess, sys, json

result = subprocess.run(
    [sys.executable, __file__.replace("_lld.py", "_check.py"), "profiles"],
    capture_output=True, text=True, timeout=10
)
if result.returncode == 0:
    print(result.stdout)
else:
    print(json.dumps([]))  # empty discovery on failure
