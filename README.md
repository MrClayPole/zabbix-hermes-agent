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

# 4. Import Template_Hermes_Agent.yaml into Zabbix Server
#    Configuration → Templates → Import → select template/Template_Hermes_Agent.yaml

# 5. Attach the template to the Hermes host
#    Configuration → Hosts → [your host] → Templates → Link "Template Hermes Agent"

# 6. Set the host macro {$HERMES.API.KEY} to your Hermes API key
#    ({$HERMES.API.HOST} and {$HERMES.API.PORT} have sensible defaults)
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
└──────────────┘     └──────────────────┘     │ + template macros │
                                              └──────────────────┘
                                                       │
                                                       ▼
                                                ┌──────────────────┐
                                                │ Zabbix Server    │
                                                │ (Template)       │
                                                │ Triggers/Graphs  │
                                                └──────────────────┘
```

Connection details (host, port, API key) are managed via **Zabbix template macros**:

- `{$HERMES.API.HOST}` — Hermes API server hostname (default: `127.0.0.1`)
- `{$HERMES.API.PORT}` — Hermes API server port (default: `8642`)
- `{$HERMES.API.KEY}` — Hermes API key (no default, set per-host)

This means the Zabbix user no longer needs read access to `.env` files.
All connection details are configured in Zabbix itself, where they belong.

### If the template import fails

Import the YAML file via Configuration → Templates → Import. If you get
UUID conflicts, open the YAML in a text editor and regenerate the
`uuid` values (use `uuidgen` or any UUID generator).

## Project Structure

```
zabbix-hermes-agent/
├── scripts/
│   ├── hermes_check.py       # Main check script (health, tokens, profiles)
│   └── hermes_lld.py         # Zabbix LLD wrapper
├── template/
│   └── Template_Hermes_Agent.yaml   # Zabbix template (7.0 LTS)
├── zabbix/
│   ├── hermes_agent2.conf    # UserParameter config for zabbix-agent2
│   └── sudoers.d/
│       └── zabbix-hermes     # Sudoers rule for zabbix user
├── LICENSE                   # MIT
└── README.md
```

## Per-Profile Gateway Monitoring

If you run multiple Hermes gateways (e.g. `default` on port 8642 and `hermes2` on port 8643), each gateway needs its own API server on a unique port:

**`~/.hermes/.env` (default):**
```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=key-default
API_SERVER_PORT=8642
```

**`~/.hermes/profiles/hermes2/.env`:**
```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=key-hermes2
API_SERVER_PORT=8643
```

The LLD discovery script reads each profile's `.env` and returns all
profiles with `API_SERVER_ENABLED=true`. Zabbix then creates item
prototypes for each discovered profile automatically.

**Important:** Set the host macro `{$HERMES.API.KEY}` to the correct API key
for each host. If you run multiple profiles on the same host, use the same
key for all profiles — the script passes the key from the macro to every
check.

## Sudoers Configuration

The scripts run as root via `sudo` (the zabbix user needs root to query the
API server endpoints). Deploy the sudoers file:

```bash
sudo cp zabbix/sudoers.d/zabbix-hermes /etc/sudoers.d/
sudo visudo -c
```

This allows the zabbix user to execute the Hermes scripts without a password.

## What It Monitors

### Per Profile (auto-discovered via LLD)

**Gateway health**
- running (1/0), active agents, platforms connected, PID
- **HIGH** trigger if gateway down

**Token consumption**
- input, output, cache read, 7d total
- **WARNING** on spike (>500 tool call change)

**Session activity**
- active sessions, total sessions, tool calls, messages
- **INFO** if idle for 1h

### Graphs

- **Token consumption** — stacked area: input/output/cache_read over time
- **Session activity** — active sessions + tool calls as dual-line

### Profile Discovery

New Hermes profiles with `API_SERVER_ENABLED=true` appear automatically
on the next Low-Level Discovery poll (default: 1 hour).

```bash
# To verify discovery:
python3 scripts/hermes_check.py profiles
# → [{"{#PROFILE}": "default"}, {"{#PROFILE}": "hermes2"}]

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

