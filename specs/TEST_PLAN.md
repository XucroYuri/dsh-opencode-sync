# Test Plan

1. Fixture: fake opencode.json + auth.json
2. Dry-run does not modify files
3. Real run writes expected refs/providers
4. Existing DSH settings are preserved
5. `opencode models --verbose` parser handles real output
