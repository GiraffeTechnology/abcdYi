# gpm-1688-pricing

OpenClaw skill skeleton for GPM Session A — 1688 pricing data ingestion.

## Overview

This skill provides the `fetch_price_samples` tool which retrieves authorized pricing data
from 1688 / Alibaba pricing-data APIs. It is backed by the Python `src/gpm` package.

## Setup

1. Copy `config.example.json` and fill in your 1688 API credentials.
2. Set the environment variables (do not hardcode credentials).
3. Use `--mode mock` for development without live API access.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GPM_1688_APP_KEY` | Live only | 1688 Open Platform app key |
| `GPM_1688_APP_SECRET` | Live only | 1688 Open Platform app secret |
| `GPM_1688_ACCESS_TOKEN` | Live only | OAuth access token |
| `GPM_1688_API_BASE_URL` | Live only | 1688 API base URL |
| `GPM_ENABLE_LIVE_1688_TESTS` | No | Set to `true` to enable live API calls |

## Usage

### Mock mode (no credentials required)

```bash
uv run python scripts/gpm_1688_api_probe.py --mode mock
```

### Live mode

```bash
GPM_ENABLE_LIVE_1688_TESTS=true uv run python scripts/gpm_1688_api_probe.py --mode live
```

## Session A Scope

This skill skeleton exposes one tool: `fetch_price_samples`.

Session B will extend this skill with pricing decision tools.
