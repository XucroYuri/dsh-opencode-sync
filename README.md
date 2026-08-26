# dsh-opencode-sync

![CI](https://github.com/XucroYuri/dsh-opencode-sync/actions/workflows/ci.yml/badge.svg) ![License](https://img.shields.io/github/license/XucroYuri/dsh-opencode-sync)

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

## Related Plugins

- [dsh-opencode-sync](https://github.com/XucroYuri/dsh-opencode-sync)
- [dsh-provider-catalog](https://github.com/XucroYuri/dsh-provider-catalog)
- [dsh-model-manager](https://github.com/XucroYuri/dsh-model-manager)
- [dsh-llm-oauth-ui](https://github.com/XucroYuri/dsh-llm-oauth-ui)
- [dsh-opencode-bridge](https://github.com/XucroYuri/dsh-opencode-bridge)

## Documentation

- [CHANGELOG.md](CHANGELOG.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [AUTHORS.md](AUTHORS.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Testing

```bash
npm test
npm run smoke
npm run pack:check
```

## Configuration

| Option | Default | Description |
|---|---|---|
| `--source` | `auto` | OpenCode config source: `windows`, `wsl`, `auto` |
| `--dsh-home` | `~/.dsh` | DSH home directory |
| `--dry-run` | false | Preview changes without writing |
| `--json` | false | JSON output |
| `--include-all-models` | false | Import every model from OpenCode |

## License

MIT
