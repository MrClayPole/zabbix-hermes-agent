# Zabbix Hermes Agent Template

Monitor [Hermes Agent](https://hermes-agent.nousresearch.com) instances via Zabbix using the built-in API Server — no SQLite scraping, no fragile CLI parsing.

## Quick Start

```bash
# 1. Deploy to the Zabbix agent host
sudo bash install.sh

# 2. Restart the agent
sudo systemctl restart zabbix-agent

# 3. Import Template_Hermes_Agent.xml into Zabbix Server
#    Configuration → Templates → Import → select template/Template_Hermes_Agent.xml

# 4. Attach the template to the Hermes host
#    Configuration → Hosts → [your host] → Templates → Link "Template Hermes Agent"
```

## Prerequisites

- **Zabbix 6.4+** (agent + server)
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
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Hermes       │────▶│ Hermes API Server│◀────│ Zabbix Agent    │
│ Gateway      │     │ :8642            │     │ (UserParameter) │
│ (profile)    │     │ /health/detailed │     │                 │
│              │     │ /api/sessions    │     │ hermes_check.py │
└──────────────┘     └──────────────────┘     └─────────────────┘
                                                       │
                                                       ▼
                                                ┌─────────────────┐
                                                │ Zabbix Server   │
                                                │ (Template)      │
                                                │ Triggers/Graphs │
                                                └─────────────────┘
```

The API Server is a standard Hermes gateway platform adapter. Each profile
runs its own gateway and (optionally) its own API server on a unique port.
The Zabbix scripts read the profile's `.env` to discover host, port, and
API key — you never pass credentials in Zabbix item keys.

## Project Structure

```
zabbix-hermes-agent/
├── scripts/
│   ├── hermes_check.py       # Main check script (health, tokens, profiles)
│   └── hermes_lld.py         # Zabbix LLD wrapper
├── template/
│   └── Template_Hermes_Agent.xml   # Zabbix template (6.4+)
├── zabbix/
│   └── hermes_agentd.conf    # UserParameter configuration
├── install.sh                # Deploy scripts + config
├── LICENSE                   # MIT
└── README.md
```

## What It Monitors

### Per Profile (auto-discovered)

| Category | Items | Trigger |
|----------|-------|---------|
| **Gateway health** | running (1/0), active agents, platforms connected, PID | HIGH if gateway down |
| **Token consumption** | input, output, cache read, 7d total | WARNING on spike (>500 tool call change) |
| **Session activity** | active sessions, total sessions, tool calls, messages | INFO if idle for 1h |

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
```

## Customisation

- **{$HERMES_TOKEN_SPIKE_THRESHOLD}** — tool call change threshold (default: 500)
- **HERMES_HOME** env var — override if Hermes lives outside `~/.hermes` (install.sh creates a wrapper)

## Token vs Cost

This template tracks **token counts**, not dollar cost. Cost estimates from
the API are client-side approximations. Tokens are exact values from the LLM
response and stable across reads.

## License

MIT