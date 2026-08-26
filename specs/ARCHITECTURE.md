# dsh-opencode-sync Architecture

## Data Flow

```text
OpenCode config/auth
  -> parse
  -> collect credentials
  -> collect provider/model metadata (opencode models --verbose)
  -> merge into DSH settings/credentials
```

## Components

- `finder`: locate Windows/WSL OpenCode paths
- `reader`: read opencode.json / auth.json
- `models`: parse `opencode models --verbose`
- `mapper`: map OpenCode provider -> DSH llm-pi-ai provider
- `writer`: merge into DSH YAML files

## DSH Seams

- `ctx.credentials` (future Cordis plugin)
- `ctx.settings` (future Cordis plugin)
- Current MVP: direct YAML file writer
