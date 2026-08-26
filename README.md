# dsh-opencode-sync

Sync OpenCode provider configurations, credentials, and model metadata into DeepSeek Harness.

> Status: Stable

## Features

- Read OpenCode config from Windows or WSL
- Import API keys into DSH credentials
- Generate llm-pi-ai provider profiles
- Dry-run support
- Native Cordis command plugin

## Requirements

- DeepSeek Harness (DSH) 0.1.1+
- OpenCode CLI (optional, for sync/catalog/bridge features)
- Node.js 22+
- Python 3.12+ (only for fallback CLI tests)

## Installation

Add the plugin to your DSH profile:

```bash
cd ~/.dsh/profiles/tools
npm install @xucroyuri/dsh-opencode-sync
```

Then add to `cordis.patch.yml`:

```yaml
- insert:
    - id: opencode-sync
      name: '@xucroyuri/dsh-opencode-sync'
```

## Usage

```bash
dsh --profile tools opencode-sync --dry-run
dsh --profile tools opencode-sync
```

## Development

```bash
node --check src/index.js
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## License

MIT
