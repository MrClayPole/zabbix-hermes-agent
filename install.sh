#!/usr/bin/env bash
# install.sh — Deploy Hermes Agent Zabbix monitoring
#
# Usage:
#   sudo bash install.sh                    # Deploy to /etc/zabbix
#   sudo bash install.sh --hermes-home /home/user/.hermes  # Custom HERMES_HOME
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ZABBIX_SCRIPT_DIR="${ZABBIX_SCRIPT_DIR:-/etc/zabbix/scripts}"
ZABBIX_CONF_DIR="${ZABBIX_CONF_DIR:-/etc/zabbix/zabbix_agentd.d}"
HERMES_HOME="${HERMES_HOME:-/root/.hermes}"

echo "==> Hermes Agent Zabbix Monitoring — Install"
echo "    Scripts:  ${ZABBIX_SCRIPT_DIR}"
echo "    Config:   ${ZABBIX_CONF_DIR}"
echo "    Hermes:   ${HERMES_HOME}"
echo ""

# ── Create directories ─────────────────────────────────────────
mkdir -p "${ZABBIX_SCRIPT_DIR}" "${ZABBIX_CONF_DIR}"

# ── Install scripts ────────────────────────────────────────────
cp "${SCRIPT_DIR}/scripts/hermes_check.py" "${ZABBIX_SCRIPT_DIR}/hermes_check.py"
cp "${SCRIPT_DIR}/scripts/hermes_lld.py"   "${ZABBIX_SCRIPT_DIR}/hermes_lld.py"
chmod 755 "${ZABBIX_SCRIPT_DIR}/hermes_check.py" "${ZABBIX_SCRIPT_DIR}/hermes_lld.py"

# ── Install Zabbix agent config ────────────────────────────────
cp "${SCRIPT_DIR}/zabbix/hermes_agentd.conf" "${ZABBIX_CONF_DIR}/hermes_agentd.conf"

# ── Set HERMES_HOME in script wrapper (optional) ───────────────
# If HERMES_HOME differs from /root/.hermes, create a wrapper that
# sets the env var before calling the real script.
if [ "${HERMES_HOME}" != "/root/.hermes" ]; then
    echo "    Creating HERMES_HOME wrapper..."
    for script in hermes_check.py hermes_lld.py; do
        wrapper="${ZABBIX_SCRIPT_DIR}/${script%.py}.sh"
        cat > "${wrapper}" <<WRAPEOF
#!/usr/bin/env bash
export HERMES_HOME="${HERMES_HOME}"
exec python3 "${ZABBIX_SCRIPT_DIR}/${script}" "\$@"
WRAPEOF
        chmod 755 "${wrapper}"
    done
fi

# ── Validate ────────────────────────────────────────────────────
echo "    Testing: hermes_check.py profiles ..."
python3 "${ZABBIX_SCRIPT_DIR}/hermes_check.py" profiles || echo "    ⚠ No profiles with API_SERVER_ENABLED found"

echo ""
echo "==> Done. Restart the Zabbix agent to pick up changes:"
echo "    sudo systemctl restart zabbix-agent"
echo ""
echo "    Then import Template_Hermes_Agent.xml into your Zabbix server."
echo "    See README.md for full instructions."
