# dsh-opencode-sync

将 OpenCode 的模型供应商配置、凭据和模型元数据同步到 DeepSeek Harness。

> 状态：稳定

## 功能特性

- 从 Windows 或 WSL 读取 OpenCode 配置
- 将 API Key 导入 DSH 凭据
- 生成 llm-pi-ai provider 配置
- 支持 dry-run 预览
- 原生 Cordis 命令插件

## 环境要求

- DeepSeek Harness (DSH) 0.1.1+
- OpenCode CLI（可选，用于 sync/catalog/bridge 功能）
- Node.js 22+
- Python 3.12+（仅用于备用 CLI 测试）

## 安装

将插件添加到 DSH profile：

```bash
cd ~/.dsh/profiles/tools
npm install @xucroyuri/dsh-opencode-sync
```

然后在 `cordis.patch.yml` 中添加：

```yaml
- insert:
    - id: opencode-sync
      name: '@xucroyuri/dsh-opencode-sync'
```

## 使用方法

```bash
dsh --profile tools opencode-sync --dry-run
dsh --profile tools opencode-sync
```

## 开发

```bash
node --check src/index.js
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## 许可证

MIT
