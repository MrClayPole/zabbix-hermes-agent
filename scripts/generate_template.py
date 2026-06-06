#!/usr/bin/env python3
"""
Generate Zabbix 7.0 LTS template XML — schema verified against C70XmlValidator.php.

Usage:
    python3 scripts/generate_template.py > Template_Hermes_Agent.xml
"""

import uuid
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

U = lambda: str(uuid.uuid4())

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

def make_item(name, keybase, delay, vtype, jpath, units=None, triggers=None):
    i = SubElement(ips, "item_prototype")
    SubElement(i, "uuid").text = U()
    SubElement(i, "name").text = f"{{#PROFILE}}: {name}"
    SubElement(i, "type").text = "ZABBIX_PASSIVE"
    SubElement(i, "key").text = f'hermes.check.{keybase}["{{#PROFILE}}"]'
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
    # Trigger prototypes (inside item_prototype, wrapper = trigger_prototypes)
    if triggers:
        tps = SubElement(i, "trigger_prototypes")
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

# ── Graph Prototypes ───────────────────────────────────────────
gps = SubElement(dr, "graph_prototypes")

def make_graph(name, items):
    gp = SubElement(gps, "graph_prototype")
    SubElement(gp, "uuid").text = U()
    SubElement(gp, "name").text = f"{{#PROFILE}}: {name}"
    SubElement(gp, "width").text = "900"
    SubElement(gp, "height").text = "200"
    SubElement(gp, "ymin_type_1").text = "CALCULATED"
    # ONE graph_items with MULTIPLE graph_item children
    gis = SubElement(gp, "graph_items")
    for sortorder, (color, calc_fnc_name, key) in enumerate(items):
        gi = SubElement(gis, "graph_item")
        SubElement(gi, "sortorder").text = str(sortorder)
        SubElement(gi, "color").text = color
        SubElement(gi, "yaxisside").text = "LEFT"
        SubElement(gi, "calc_fnc").text = calc_fnc_name
        SubElement(gi, "type").text = "SIMPLE"
        ir = SubElement(gi, "item")
        SubElement(ir, "host").text = "Template Hermes Agent"
        SubElement(ir, "key").text = key

make_graph("Token consumption", [
    ("1A7BFF", "LAST", 'hermes.check.tokens["{#PROFILE}"]'),
    ("00E676", "LAST", 'hermes.check.tokens["{#PROFILE}"]'),
    ("FF9100", "LAST", 'hermes.check.tokens["{#PROFILE}"]'),
])
make_graph("Session activity", [
    ("1A7BFF", "AVG", 'hermes.check.tokens["{#PROFILE}"]'),
    ("00E676", "AVG", 'hermes.check.tokens["{#PROFILE}"]'),
])

# ── Output without minidom (avoids text node issues) ───────────
rough = tostring(z, encoding="unicode")
# minidom for pretty-printing, but strip the XML declaration since
# ElementTree already adds it
dom = minidom.parseString(rough.encode("utf-8"))
print(dom.toprettyxml(indent="    "))