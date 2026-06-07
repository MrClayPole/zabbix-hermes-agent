#!/usr/bin/env python3
"""
Generate Zabbix 7.0 LTS template XML — schema verified against C70XmlValidator.php.

Usage:
    python3 scripts/generate_template.py > Template_Hermes_Agent.xml
"""

import uuid
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

U = lambda: uuid.uuid4().hex  # 32 hex chars, no hyphens (Zabbix 7.0 requirement)

z = Element("zabbix_export")
SubElement(z, "version").text = "7.0"

# ── Template group ─────────────────────────────────────────────
tgs = SubElement(z, "template_groups")
tg = SubElement(tgs, "template_group")
SubElement(tg, "uuid").text = U()
SubElement(tg, "name").text = "Templates/Applications"

# ── Template ───────────────────────────────────────────────────
ts = SubElement(z, "templates")
t = SubElement(ts, "template")
SubElement(t, "uuid").text = U()
SubElement(t, "template").text = "Template Hermes Agent"
SubElement(t, "name").text = "Template Hermes Agent"
SubElement(t, "description").text = (
    "Zabbix template for monitoring Hermes Agent via its built-in "
    "API Server. Monitors gateway health, platform connectivity, "
    "token consumption, session activity, and tool usage."
)
grps = SubElement(t, "groups")
g = SubElement(grps, "group")
SubElement(g, "name").text = "Templates/Applications"
SubElement(t, "items")

# ── Template Macros ────────────────────────────────────────────
# These are set per-host when the template is assigned.
# Passed through item keys as positional parameters to hermes_check.py.
macros_el = SubElement(t, "macros")

macro_host = SubElement(macros_el, "macro")
SubElement(macro_host, "macro").text = "{$HERMES.API.HOST}"
SubElement(macro_host, "value").text = "127.0.0.1"
SubElement(macro_host, "description").text = "Hermes API server hostname or IP"

macro_port = SubElement(macros_el, "macro")
SubElement(macro_port, "macro").text = "{$HERMES.API.PORT}"
SubElement(macro_port, "value").text = "8642"
SubElement(macro_port, "description").text = "Hermes API server port"

macro_key = SubElement(macros_el, "macro")
SubElement(macro_key, "macro").text = "{$HERMES.API.KEY}"
SubElement(macro_key, "value").text = ""
SubElement(macro_key, "description").text = "Hermes API server key (set per-host)"

# ── Discovery Rule ─────────────────────────────────────────────
drs = SubElement(t, "discovery_rules")
dr = SubElement(drs, "discovery_rule")
SubElement(dr, "uuid").text = U()
SubElement(dr, "name").text = "Discover Hermes Profiles"
SubElement(dr, "type").text = "ZABBIX_PASSIVE"
SubElement(dr, "key").text = "hermes.profiles.discovery"
SubElement(dr, "delay").text = "1h"
flt = SubElement(dr, "filter")
SubElement(flt, "evaltype").text = "AND_OR"
conds = SubElement(flt, "conditions")
c = SubElement(conds, "condition")
SubElement(c, "macro").text = "{#PROFILE}"
SubElement(c, "value").text = ".*"
SubElement(c, "operator").text = "MATCHES_REGEX"
SubElement(c, "formulaid").text = "A"
SubElement(dr, "lifetime_type").text = "DELETE_AFTER"
SubElement(dr, "lifetime").text = "7d"

# ── Item Prototypes ────────────────────────────────────────────
ips = SubElement(dr, "item_prototypes")

def make_item(name, keybase, delay, vtype, jpath, field, units=None):
    i = SubElement(ips, "item_prototype")
    SubElement(i, "uuid").text = U()
    SubElement(i, "name").text = f"{{#PROFILE}}: {name}"
    SubElement(i, "type").text = "ZABBIX_PASSIVE"
    # Key includes host/port/key macros passed through from template
    SubElement(i, "key").text = (
        f'hermes.check["{keybase}","{field}","{{#PROFILE}}",'
        f'"{{$HERMES.API.HOST}}","{{$HERMES.API.PORT}}","{{$HERMES.API.KEY}}"]'
    )
    SubElement(i, "delay").text = delay
    SubElement(i, "value_type").text = vtype
    if units:
        SubElement(i, "units").text = units
    # Preprocessing
    pp = SubElement(i, "preprocessing")
    s = SubElement(pp, "step")
    SubElement(s, "type").text = "JSONPATH"
    par = SubElement(s, "parameters")
    SubElement(par, "parameter").text = jpath

make_item("Gateway running",       "health", "1m", "UNSIGNED", "$.gateway_up",  "gateway_up")
make_item("Active agents",         "health", "1m", "UNSIGNED", "$.active_agents", "active_agents")
make_item("Platforms connected",   "health", "1m", "UNSIGNED", "$.platforms_connected", "platforms_connected")
make_item("Platforms total",       "health", "1m", "UNSIGNED", "$.platforms_total", "platforms_total")
make_item("Gateway PID",           "health", "5m", "UNSIGNED", "$.pid", "pid")
make_item("Input tokens",          "tokens", "5m", "UNSIGNED", "$.total_input_tokens", "input_tokens", "tokens")
make_item("Output tokens",         "tokens", "5m", "UNSIGNED", "$.total_output_tokens", "output_tokens", "tokens")
make_item("Cache read tokens",     "tokens", "5m", "UNSIGNED", "$.total_cache_read_tokens", "cache_read_tokens", "tokens")
make_item("Tokens (7d)",           "tokens", "5m", "UNSIGNED", "$.tokens_7d", "tokens_7d", "tokens")
make_item("Active sessions",       "tokens", "5m", "UNSIGNED", "$.active_sessions", "active_sessions")
make_item("Total sessions",        "tokens", "5m", "UNSIGNED", "$.total_sessions", "total_sessions")
make_item("Tool calls",            "tokens", "5m", "UNSIGNED", "$.total_tool_calls", "tool_calls")
make_item("Messages",              "tokens", "5m", "UNSIGNED", "$.total_messages", "total_messages")

# ── Graph Prototypes ───────────────────────────────────────────
gps = SubElement(dr, "graph_prototypes")


def _macro_key(keybase, field):
    """Build a graph key matching the item prototype key pattern."""
    return (
        f'hermes.check["{keybase}","{field}","{{#PROFILE}}",'
        f'"{{$HERMES.API.HOST}}","{{$HERMES.API.PORT}}","{{$HERMES.API.KEY}}"]'
    )


def make_graph(name, items):
    gp = SubElement(gps, "graph_prototype")
    SubElement(gp, "uuid").text = U()
    SubElement(gp, "name").text = f"{{#PROFILE}}: {name}"
    SubElement(gp, "width").text = "900"
    SubElement(gp, "height").text = "200"
    SubElement(gp, "ymin_type_1").text = "CALCULATED"
    gis = SubElement(gp, "graph_items")
    for sortorder, (color, calc_fnc_name, keybase, field) in enumerate(items):
        gi = SubElement(gis, "graph_item")
        SubElement(gi, "sortorder").text = str(sortorder)
        SubElement(gi, "color").text = color
        SubElement(gi, "yaxisside").text = "LEFT"
        SubElement(gi, "calc_fnc").text = calc_fnc_name
        SubElement(gi, "type").text = "SIMPLE"
        ir = SubElement(gi, "item")
        SubElement(ir, "host").text = "Template Hermes Agent"
        SubElement(ir, "key").text = _macro_key(keybase, field)


make_graph("Token consumption", [
    ("1A7BFF", "LAST", "tokens", "input_tokens"),
    ("00E676", "LAST", "tokens", "output_tokens"),
    ("FF9100", "LAST", "tokens", "cache_read_tokens"),
])
make_graph("Session activity", [
    ("1A7BFF", "AVG", "tokens", "active_sessions"),
    ("00E676", "AVG", "tokens", "total_sessions"),
])

# ── Trigger Prototypes (Zabbix 7.0: func(/host/key, params) format) ──
tps = SubElement(dr, "trigger_prototypes")


def _trigger_key(keybase, field):
    """Build a trigger expression key with macros."""
    return (
        f'/Template Hermes Agent/hermes.check["{keybase}","{field}",'
        f'"{{#PROFILE}}","{{$HERMES.API.HOST}}","{{$HERMES.API.PORT}}","{{$HERMES.API.KEY}}"]'
    )


# Trigger: Gateway down
tp1 = SubElement(tps, "trigger_prototype")
SubElement(tp1, "uuid").text = U()
SubElement(tp1, "expression").text = f'last({_trigger_key("health","gateway_up")})=0'
SubElement(tp1, "name").text = '{#PROFILE}: Gateway process is down'
SubElement(tp1, "priority").text = "HIGH"

# Trigger: No active sessions
tp2 = SubElement(tps, "trigger_prototype")
SubElement(tp2, "uuid").text = U()
SubElement(tp2, "expression").text = (
    f'last({_trigger_key("tokens","active_sessions")})=0'
    ' and '
    f'avg({_trigger_key("tokens","active_sessions")},1h)=0'
)
SubElement(tp2, "name").text = '{#PROFILE}: No active sessions for 1h'
SubElement(tp2, "priority").text = "INFO"

# Trigger: Tool call spike
tp3 = SubElement(tps, "trigger_prototype")
SubElement(tp3, "uuid").text = U()
SubElement(tp3, "expression").text = f'change({_trigger_key("tokens","tool_calls")})>500'
SubElement(tp3, "name").text = '{#PROFILE}: Tool call spike'
SubElement(tp3, "priority").text = "WARNING"

# ── Output without minidom (avoids text node issues) ───────────
rough = tostring(z, encoding="unicode")
# minidom for pretty-printing, but strip the XML declaration since
# ElementTree already adds it
dom = minidom.parseString(rough.encode("utf-8"))
print(dom.toprettyxml(indent="    "))
