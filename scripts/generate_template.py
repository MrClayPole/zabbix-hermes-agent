#!/usr/bin/env python3
"""Generate a minimal Zabbix 7.0 template XML. Use this if the pre-built
XML in template/ fails to import — it generates everything locally with
proper UUIDs.

Usage:
    python3 scripts/generate_template.py > Template_Hermes_Agent.xml
"""

import uuid
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

U = lambda: str(uuid.uuid4())

z = Element("zabbix_export")
SubElement(z, "version").text = "7.0"
SubElement(z, "date").text = "2026-06-06T00:00:00Z"

# Template group
tgs = SubElement(z, "template_groups")
tg = SubElement(tgs, "template_group")
SubElement(tg, "uuid").text = U()
SubElement(tg, "name").text = "Templates/Applications"

# Template
ts = SubElement(z, "templates")
t = SubElement(ts, "template")
SubElement(t, "uuid").text = U()
SubElement(t, "template").text = "Template Hermes Agent"
SubElement(t, "name").text = "Template Hermes Agent"
SubElement(t, "description").text = (
    "Zabbix template for monitoring Hermes Agent. "
    "Uses the built-in API Server to collect gateway health, "
    "token consumption, and session metrics."
)
grps = SubElement(t, "groups")
SubElement(grps, "group").text = "Templates/Applications"

# Empty items
SubElement(t, "items")

# Discovery rule
drs = SubElement(t, "discovery_rules")
dr = SubElement(drs, "discovery_rule")
SubElement(dr, "uuid").text = U()
SubElement(dr, "name").text = "Discover Hermes Profiles"
SubElement(dr, "type").text = "ZABBIX_AGENT"
SubElement(dr, "key").text = "hermes.profiles.discovery"
SubElement(dr, "delay").text = "1h"
SubElement(dr, "keep_lost_resources").text = "1d"

# Filter
flt = SubElement(dr, "filter")
conds = SubElement(flt, "conditions")
c = SubElement(conds, "condition")
SubElement(c, "macro").text = "{#PROFILE}"
SubElement(c, "value").text = ".*"
SubElement(c, "formulaid").text = "A"
SubElement(c, "operator").text = "REGEXP"

# Item prototypes
ITEMS = [
    ("Gateway running",       "health", "1m", "UNSIGNED", "$.gateway_up", "tokens",
     [("Gateway process is down", "{last()}=0", "HIGH")]),
    ("Active agents",         "health", "1m", "UNSIGNED", "$.active_agents", None, []),
    ("Platforms connected",   "health", "1m", "UNSIGNED", "$.platforms_connected", None, []),
    ("Platforms total",       "health", "1m", "UNSIGNED", "$.platforms_total", None, []),
    ("Gateway PID",           "health", "5m", "UNSIGNED", "$.pid", None, []),
    ("Input tokens",          "tokens", "5m", "UNSIGNED", "$.total_input_tokens", "tokens", []),
    ("Output tokens",         "tokens", "5m", "UNSIGNED", "$.total_output_tokens", "tokens", []),
    ("Cache read tokens",     "tokens", "5m", "UNSIGNED", "$.total_cache_read_tokens", "tokens", []),
    ("Tokens (7d)",           "tokens", "5m", "UNSIGNED", "$.tokens_7d", "tokens", []),
    ("Active sessions",       "tokens", "5m", "UNSIGNED", "$.active_sessions", None,
     [("No active sessions for 1h", "{last()}=0 and {avg(1h)}=0", "INFO")]),
    ("Total sessions",        "tokens", "5m", "UNSIGNED", "$.total_sessions", None, []),
    ("Tool calls",            "tokens", "5m", "UNSIGNED", "$.total_tool_calls", None,
     [("Tool call spike", "{change()}>500", "WARNING")]),
    ("Messages",              "tokens", "5m", "UNSIGNED", "$.total_messages", None, []),
]

for name, keybase, delay, vtype, jpath, units, triggers in ITEMS:
    ip = SubElement(dr, "item_prototypes")
    i = SubElement(ip, "item_prototype")
    SubElement(i, "uuid").text = U()
    SubElement(i, "name").text = f"{{#PROFILE}}: {name}"
    SubElement(i, "type").text = "ZABBIX_AGENT"
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

    for tp_name, tp_expr, tp_pri in triggers:
        tps = SubElement(i, "triggers")
        tp = SubElement(tps, "trigger_prototype")
        SubElement(tp, "uuid").text = U()
        SubElement(tp, "expression").text = tp_expr
        SubElement(tp, "name").text = f"{{#PROFILE}}: {tp_name}"
        SubElement(tp, "priority").text = tp_pri

# Graph prototypes
GRAPH_ITEMS = {
    "Token consumption": [("1A7BFF", "7", "$.total_input_tokens"),
                           ("00E676", "7", "$.total_output_tokens"),
                           ("FF9100", "7", "$.total_cache_read_tokens")],
    "Session activity":  [("1A7BFF", "2", "$.active_sessions"),
                           ("00E676", "2", "$.total_tool_calls")],
}

for gname, gitems in GRAPH_ITEMS.items():
    gps = SubElement(dr, "graph_prototypes")
    gp = SubElement(gps, "graph_prototype")
    SubElement(gp, "uuid").text = U()
    SubElement(gp, "name").text = f"{{#PROFILE}}: {gname}"
    SubElement(gp, "width").text = "900"
    SubElement(gp, "height").text = "200"
    SubElement(gp, "ymin_type_1").text = "0"
    for color, calc, _ in gitems:
        gi = SubElement(gp, "graph_items")
        gi_e = SubElement(gi, "graph_item")
        SubElement(gi_e, "sortorder").text = "0"
        item_ref = SubElement(gi_e, "item")
        SubElement(item_ref, "host").text = "Template Hermes Agent"
        SubElement(item_ref, "key").text = f'hermes.check.tokens["{{#PROFILE}}"]'
        SubElement(gi_e, "color").text = color
        SubElement(gi_e, "yaxisside").text = "0"
        SubElement(gi_e, "calc_fnc").text = calc
        SubElement(gi_e, "type").text = "0"

# Output
rough = tostring(z, encoding="unicode")
parsed = minidom.parseString(rough.encode("utf-8"))
print(parsed.toprettyxml(indent="    "))