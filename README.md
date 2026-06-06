# Zabbix Hermes Agent Template

Monitor [Hermes Agent](https://hermes-agent.nousresearch.com) instances via Zabbix using the built-in API Server — no SQLite scraping, no fragile CLI parsing.

## Quick Start

```bash
# 1. Deploy scripts to the Zabbix agent host
sudo mkdir -p /etc/zabbix/scripts
sudo cp scripts/hermes_check.py scripts/hermes_lld.py /etc/zabbix/scripts/
sudo chmod 755 /etc/zabbix/scripts/hermes_check.py /etc/zabbix/scripts/hermes_lld.py

# 2. Deploy the agent2 config
sudo cp zabbix/hermes_agent2.conf /etc/zabbix/zabbix_agent2.d/hermes_agent.conf

# 3. Restart the agent2 service
sudo systemctl restart zabbix-agent2

# 4. Import Template_Hermes_Agent.xml into Zabbix Server
#    Configuration → Templates → Import → select template/Template_Hermes_Agent.xml

# 5. Attach the template to the Hermes host
#    Configuration → Hosts → [your host] → Templates → Link "Template Hermes Agent"
```

## Prerequisites

- **Zabbix 7.0 LTS** (agent2 + server)
- **Hermes Agent** with `API_SERVER_ENABLED=true` in the target profile's `.env`

Add to `~/.hermes/.env` (or `~/.hermes/profiles/<name>/.env`):

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=generate-a-random-key-here
API_SERVER_PORT=8642
API_SERVER_HOST=127.0.0.1
```

Restart the Hermes gateway after adding these.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Hermes       │────▶│ Hermes API Server│◀────│ Zabbix agent2    │
│ Gateway      │     │ :8642            │     │ (UserParameter)  │
│ (profile)    │     │ /health/detailed │     │                  │
│              │     │ /api/sessions    │     │ hermes_check.py  │
└──────────────┘     └──────────────────┘     └──────────────────┘
                                                       │
                                                       ▼
                                                ┌──────────────────┐
                                                │ Zabbix Server    │
                                                │ (Template)       │
                                                │ Triggers/Graphs  │
                                                └──────────────────┘
```

The API Server is a standard Hermes gateway platform adapter. Each profile
runs its own gateway and (optionally) its own API server on a unique port.
The Zabbix scripts read the profile's `.env` to discover host, port, and
API key — you never pass credentials in Zabbix item keys.

### If the template import fails

Run the generator script on the Zabbix server to produce a fresh XML with
locally-generated UUIDs:

```bash
python3 scripts/generate_template.py > Template_Hermes_Agent.xml
```

Then import the generated file via Configuration → Templates → Import.

## Project Structure

```
zabbix-hermes-agent/
├── scripts/
│   ├── hermes_check.py       # Main check script (health, tokens, profiles)
│   ├── hermes_lld.py         # Zabbix LLD wrapper
│   └── generate_template.py  # Regenerate template XML locally
├── template/
│   └── Template_Hermes_Agent.xml   # Zabbix template (7.0 LTS)
├── zabbix/
│   └── hermes_agent2.conf    # UserParameter config for zabbix-agent2
├── LICENSE                   # MIT
└── README.md
```

## Per-Profile Gateway Monitoring

If you run multiple Hermes gateways (e.g. `default` on port 8642 and `glados` on port 8643), each gateway needs its own API server on a unique port:

**`~/.hermes/.env` (default):**
```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=key-default
API_SERVER_PORT=8642
```

**`~/.hermes/profiles/glados/.env`:**
```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=key-glados
API_SERVER_PORT=8643
```

The LLD discovery script reads each profile's `.env` and returns all
profiles with `API_SERVER_ENABLED=true`. Zabbix then creates item
prototypes for each discovered profile automatically.

## What It Monitors

### Per Profile (auto-discovered via LLD)

| Category | Items | Trigger |
|----------|-------|---------|
| **Gateway health** | running (1/0), active agents, platforms connected, PID | **HIGH** if gateway down |
| **Token consumption** | input, output, cache read, 7d total | **WARNING** on spike (>500 tool call change) |
| **Session activity** | active sessions, total sessions, tool calls, messages | **INFO** if idle for 1h |

### Graphs

- **Token consumption** — stacked area: input/output/cache_read over time
- **Session activity** — active sessions + tool calls as dual-line

### Profile Discovery

New Hermes profiles with `API_SERVER_ENABLED=true` appear automatically
on the next Low-Level Discovery poll (default: 1 hour).

```bash
# To verify discovery:
python3 scripts/hermes_check.py profiles
# → [{"{#PROFILE}": "default"}, {"{#PROFILE}": "glados"}]

# Test gateway health for a specific profile:
python3 scripts/hermes_check.py health default
# → {"gateway_up": 1, "active_agents": 0, ...}

# Test token aggregation:
python3 scripts/hermes_check.py tokens default
# → {"total_input_tokens": 71651198, "total_output_tokens": 1032342, ...}
```

## Token vs Cost

This template tracks **token counts**, not dollar cost. Cost estimates from
the API are client-side approximations. Tokens are exact values from the LLM
response and stable across reads. The `cache_read_tokens` metric is
especially useful — if the cache hit ratio drops, your sessions are
diverging and both latency and real cost go up.

## License

MIT

Copyright (c) 2026 Mat Clarke