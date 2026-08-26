# Security

- API keys only written to `~/.dsh/.credentials.yaml` (mode 0600).
- Never write keys into `settings.yaml`.
- OAuth tokens are not written by default.
- Paths are resolved safely; no shell interpolation.
