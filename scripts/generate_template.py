#!/usr/bin/env python3
"""Generate a Zabbix 7.0 template XML for Hermes Agent monitoring.

Usage:
    python3 scripts/generate_template.py > Template_Hermes_Agent.xml
"""

import uuid
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

U = lambda: str(uuid.uuid4())

z = Element("zabbix_export")
SubElement(z, "version").text = "7.0"

tgs = SubElement(z, "template_groups")
tg = SubElement(tgs, "template_group")
SubElement(tg, "uuid").text = U()
SubElement(tg, "name").text = "Templates/Applications"

ts = SubElement(z, "templates")
t = SubElement(ts, "template")
SubElement(t, "uuid").text = U()
SubElement(t, "template").text = "Template Hermes Agent"
SubElement(t, "name").text = "Template Hermes Agent"
SubElement(t, "description").text = (
    "Zabbix template for monitoring Hermes Agent via its built-in "
    "API Server. Monitors gateway health, platform connectivity, "
    "token consumption, session activity, and tool usage across "
    "Hermes profiles with API_SERVER_ENABLED=true."
)
grps = SubElement(t, "groups")
g = SubElement(grps, "group")
SubElement(g, "name").text = "Templates/Applications"
SubElement(t, "items")

# ── Discovery Rule ─────────────────────────────────────────────
drs = SubElement(t, "discovery_rules")
dr = SubElement(drs, "discovery_rule")
SubElement(dr, "uuid").text = U()
SubElement(dr, "name").text = "Discover Hermes Profiles"
SubElement(dr, "type").text = "ZABBIX"
SubElement(dr, "key").text = "hermes.profiles.discovery"
SubElement(dr, "delay").text = "1h"
flt = SubElement(dr, "filter")
conds = SubElement(flt, "conditions")
c = SubElement(conds, "condition")
SubElement(c, "macro").text = "{#PROFILE}"
SubElement(c, "value").text = ".*"
SubElement(c, "formulaid").text = "A"
SubElement(c, "operator").text = "REGEXP"

# ── Item Prototypes (all under one <item_prototypes>) ──────────
ips = SubElement(dr, "item_prototypes")

def make_item(name, keybase, delay, vtype, jpath, units=None, triggers=None):
    i = SubElement(ips, "item_prototype")
    SubElement(i, "uuid").text = U()
    SubElement(i, "name").text = f"{{#PROFILE}}: {name}"
    SubElement(i, "type").text = "ZABBIX"
    SubElement(i, "key").text = f'hermes.check.{keybase}["{{#PROFILE}}"]'
    SubElement(i, "delay").text = delay
    SubElement(i, "value_type").text = vtype
    if units:
        SubElement(i, "units").text = units
    pp = SubElement(i, "preprocessing")
    s = SubElement(pp, "step")
    SubElement(s, "type").text = "JSONPATH"
    par = SubElement(s, "parameters")
    SubElement(par, "parameter").text = jpath
    if triggers:
        tps = SubElement(i, "triggers")
        for tp_name, tp_expr, tp_pri in triggers:
            tp = SubElement(tps, "trigger_prototype")
            SubElement(tp, "uuid").text = U()
            SubElement(tp, "expression").text = tp_expr
            SubElement(tp, "name").text = f"{{#PROFILE}}: {tp_name}"
            SubElement(tp, "priority").text = tp_pri

make_item("Gateway running",       "health", "1m", "UNSIGNED", "$.gateway_up", None,
          [("Gateway process is down", "{last()}=0", "HIGH")])
make_item("Active agents",         "health", "1m", "UNSIGNED", "$.active_agents")
make_item("Platforms connected",   "health", "1m", "UNSIGNED", "$.platforms_connected")
make_item("Platforms total",       "health", "1m", "UNSIGNED", "$.platforms_total")
make_item("Gateway PID",           "health", "5m", "UNSIGNED", "$.pid")
make_item("Input tokens",          "tokens", "5m", "UNSIGNED", "$.total_input_tokens", "tokens")
make_item("Output tokens",         "tokens", "5m", "UNSIGNED", "$.total_output_tokens", "tokens")
make_item("Cache read tokens",     "tokens", "5m", "UNSIGNED", "$.total_cache_read_tokens", "tokens")
make_item("Tokens (7d)",           "tokens", "5m", "UNSIGNED", "$.tokens_7d", "tokens")
make_item("Active sessions",       "tokens", "5m", "UNSIGNED", "$.active_sessions", None,
          [("No active sessions for 1h", "{last()}=0 and {avg(1h)}=0", "INFO")])
make_item("Total sessions",        "tokens", "5m", "UNSIGNED", "$.total_sessions")
make_item("Tool calls",            "tokens", "5m", "UNSIGNED", "$.total_tool_calls", None,
          [("Tool call spike", "{change()}>500", "WARNING")])
make_item("Messages",              "tokens", "5m", "UNSIGNED", "$.total_messages")

# ── Graph Prototypes (all under one <graph_prototypes>) ────────
gps = SubElement(dr, "graph_prototypes")

def make_graph(name, items):
    gp = SubElement(gps, "graph_prototype")
    SubElement(gp, "uuid").text = U()
    SubElement(gp, "name").text = f"{{#PROFILE}}: {name}"
    SubElement(gp, "width").text = "900"
    SubElement(gp, "height").text = "200"
    SubElement(gp, "ymin_type_1").text = "0"
    for color, calc, key in items:
        gi = SubElement(gp, "graph_items")
        gi_e = SubElement(gi, "graph_item")
        SubElement(gi_e, "sortorder").text = "0"
        ir = SubElement(gi_e, "item")
        SubElement(ir, "host").text = "Template Hermes Agent"
        SubElement(ir, "key").text = key
        SubElement(gi_e, "color").text = color
        SubElement(gi_e, "yaxisside").text = "0"
        SubElement(gi_e, "calc_fnc").text = calc
        SubElement(gi_e, "type").text = "0"

make_graph("Token consumption", [
    ("1A7BFF", "7", 'hermes.check.tokens["{#PROFILE}"]'),
    ("00E676", "7", 'hermes.check.tokens["{#PROFILE}"]'),
    ("FF9100", "7", 'hermes.check.tokens["{#PROFILE}"]'),
])
make_graph("Session activity", [
    ("1A7BFF", "2", 'hermes.check.tokens["{#PROFILE}"]'),
    ("00E676", "2", 'hermes.check.tokens["{#PROFILE}"]'),
])

# ── Output ─────────────────────────────────────────────────────
rough = tostring(z, encoding="unicode")
parsed = minidom.parseString(rough.encode("utf-8"))
print(parsed.toprettyxml(indent="    "))