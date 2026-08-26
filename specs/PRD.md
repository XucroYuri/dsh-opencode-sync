# dsh-opencode-sync PRD

## Problem Statement

用户同时使用 Windows/WSL 上的 OpenCode 和 WSL 中的 DeepSeek Harness。
OpenCode 中已经配置了大量模型供应商和凭据，但 DSH 中需要手动重复配置，
导致模型接入成本高、容易不一致。

## Goals

- 从 OpenCode 配置中读取 provider / model / credentials。
- 将 API Key 写入 DSH `~/.dsh/.credentials.yaml`。
- 将 provider/model 配置写入 DSH `~/.dsh/settings.yaml` 的 `llm-pi-ai.providers`。
- 支持 `--dry-run`。
- 支持 Windows 和 WSL 两种 OpenCode 配置来源。

## Non-Goals

- 不替代 DSH 原生 OAuth 登录。
- 不保证 OAuth token 自动刷新。
- 不修改 DSH 核心代码。

## User Stories

- 作为 DSH 用户，我希望运行一条命令后，OpenCode 里的 DeepSeek/ZAI 等 provider 自动出现在 DSH 中。
- 作为 DSH 用户，我希望先预览再写入，避免破坏现有配置。
