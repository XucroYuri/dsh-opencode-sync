#!/usr/bin/env python3
"""dsh-opencode-sync: import OpenCode provider config into DeepSeek Harness.

This is the MVP CLI. A later Cordis plugin will wrap the same logic in
ctx.settings / ctx.credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("dsh-opencode-sync requires PyYAML (pip install pyyaml)") from exc


def env_name(provider: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", provider).strip("_").upper() + "_API_KEY"


def load_json(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def find_windows_opencode() -> dict[str, pathlib.Path]:
    root = pathlib.Path("/mnt/c/Users")
    if not root.exists():
        raise SystemExit("No /mnt/c/Users found; are you inside WSL?")
    for user_dir in sorted(root.iterdir()):
        cfg = user_dir / ".config/opencode/opencode.json"
        auth = user_dir / ".local/share/opencode/auth.json"
        if cfg.exists() or auth.exists():
            return {"user": user_dir, "config": cfg, "auth": auth}
    raise SystemExit("No OpenCode Windows config found under /mnt/c/Users")


def find_wsl_opencode() -> dict[str, pathlib.Path]:
    home = pathlib.Path.home()
    cfg = home / ".config/opencode/opencode.json"
    auth = home / ".local/share/opencode/auth.json"
    if not cfg.exists() and not auth.exists():
        raise SystemExit("No OpenCode WSL config found under ~/.config/opencode")
    return {"user": home, "config": cfg, "auth": auth}


def parse_opencode_models() -> list[tuple[str, dict]]:
    """Parse `opencode models --verbose` output into (provider/model, metadata)."""
    try:
        out = subprocess.check_output(
            ["opencode", "models", "--verbose"],
            text=True,
            timeout=60,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Could not run `opencode models --verbose`: {exc}") from exc

    lines = out.splitlines()
    entries: list[tuple[str, dict]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line and "/" in line and not line.startswith("{") and not line.startswith("}"):
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and lines[j].strip() == "{":
                text = "\n".join(lines[j:])
                obj, end = json.JSONDecoder().raw_decode(text)
                entries.append((line, obj))
                i = j + text[:end].count("\n") + 1
                continue
        i += 1
    return entries


def collect_secrets(opencode_cfg: dict, auth: dict) -> tuple[dict[str, str], dict[str, str]]:
    refs: dict[str, str] = {}
    provider_ref: dict[str, str] = {}

    def add(provider: str, key: str) -> None:
        ref = env_name(provider)
        refs[ref] = key
        provider_ref[provider] = ref

    for pid, pconf in opencode_cfg.get("provider", {}).items():
        if not isinstance(pconf, dict):
            continue
        opts = pconf.get("options", {})
        if not isinstance(opts, dict):
            opts = {}
        key = opts.get("apiKey") or pconf.get("apiKey")
        if isinstance(key, str) and key:
            add(pid, key)

    for pid, aconf in auth.items():
        if not isinstance(aconf, dict):
            continue
        if aconf.get("type") == "api" and isinstance(aconf.get("key"), str) and aconf["key"]:
            add(pid, aconf["key"])

    return refs, provider_ref


def build_profiles(
    models: list[tuple[str, dict]],
    provider_ref: dict[str, str],
    existing_providers: dict | None = None,
    preferred_models: dict[str, set[str]] | None = None,
    include_all_models: bool = False,
) -> dict[str, dict]:
    by_provider: dict[str, list[tuple[str, dict]]] = {}
    for full, meta in models:
        provider, _, model_id = full.partition("/")
        by_provider.setdefault(provider, []).append((model_id, meta))

    known_catalog = {
        "openai", "deepseek", "anthropic", "google", "xai",
        "zai", "opencode", "github-copilot",
    }
    existing_providers = existing_providers or {}
    preferred_models = preferred_models or {}

    providers: dict[str, dict] = {}
    for provider, model_list in by_provider.items():
        if provider not in provider_ref:
            continue

        profile: dict = {"apiKeyEnv": provider_ref[provider]}
        first = model_list[0][1] if model_list else {}
        api_info = first.get("api", {}) or {}
        url = api_info.get("url")
        if url:
            profile["baseURL"] = url

        is_known = provider in known_catalog
        if not is_known:
            profile["api"] = "openai-completions"

        existing_models = None
        existing_provider = existing_providers.get(provider)
        if isinstance(existing_provider, dict):
            em = existing_provider.get("models")
            if isinstance(em, list):
                existing_models = em

        dsh_models = []
        if existing_models is not None:
            # Preserve the user's existing allowlist exactly.
            dsh_models = existing_models
        elif is_known and not include_all_models:
            # Known pi-ai catalog routes can use the built-in catalog when the
            # user has not explicitly configured a model allowlist.
            dsh_models = []
        else:
            pref = preferred_models.get(provider)
            for model_id, meta in model_list:
                if pref is not None and model_id not in pref:
                    continue
                entry: dict = {"id": model_id}
                name = meta.get("name")
                if isinstance(name, str) and name and name != model_id:
                    entry["name"] = name
                limit = meta.get("limit", {}) or {}
                if limit.get("context"):
                    entry["contextWindow"] = limit["context"]
                if limit.get("output"):
                    entry["maxTokens"] = limit["output"]
                variants = meta.get("variants", {}) or {}
                efforts = {}
                for level, variant in variants.items():
                    if isinstance(variant, dict) and variant.get("effort"):
                        efforts[level] = variant["effort"]
                if efforts:
                    entry["reasoningEfforts"] = efforts
                dsh_models.append(entry)

        if dsh_models:
            profile["models"] = dsh_models
        providers[provider] = profile

    return providers


def merge_settings(existing: dict, providers: dict[str, dict]) -> dict:
    result = dict(existing)
    llm = dict(result.get("llm-pi-ai", {}) or {})
    provs = dict(llm.get("providers", {}) or {})
    provs.update(providers)
    llm["providers"] = provs
    result["llm-pi-ai"] = llm
    return result


def merge_credentials(existing: dict, refs: dict[str, str]) -> dict:
    result = dict(existing)
    if "version" not in result:
        result = {"version": 1, **result}
    ref_section = dict(result.get("refs", {}) or {})
    ref_section.update(refs)
    result["refs"] = ref_section
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dsh-home", default=os.environ.get("DSH_HOME") or str(pathlib.Path.home() / ".dsh"))
    ap.add_argument("--source", choices=["windows", "wsl", "auto"], default="auto")
    ap.add_argument("--dry-run", action="store_true", help="print changes without writing")
    ap.add_argument("--include-all-models", action="store_true", help="import every model from OpenCode instead of preserving/allowlisting")
    args = ap.parse_args(argv)

    if args.source == "windows":
        src = find_windows_opencode()
    elif args.source == "wsl":
        src = find_wsl_opencode()
    else:
        try:
            src = find_windows_opencode()
        except SystemExit:
            src = find_wsl_opencode()

    opencode_cfg = load_json(src["config"])
    auth = load_json(src["auth"])

    refs, provider_ref = collect_secrets(opencode_cfg, auth)
    if not provider_ref:
        print("No API-key providers found in OpenCode config/auth.", file=sys.stderr)
        return 1

    models = parse_opencode_models()

    dsh_home = pathlib.Path(args.dsh_home)
    creds_path = dsh_home / ".credentials.yaml"
    settings_path = dsh_home / "settings.yaml"
    creds = yaml.safe_load(creds_path.read_text(encoding="utf-8")) if creds_path.exists() else {}
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    existing_providers = {}
    if isinstance(settings, dict):
        llm = settings.get("llm-pi-ai", {})
        if isinstance(llm, dict):
            existing_providers = llm.get("providers", {}) or {}

    preferred_models: dict[str, set[str]] = {}
    for key in ("model", "small_model"):
        val = opencode_cfg.get(key)
        if isinstance(val, str) and "/" in val:
            provider, _, model_id = val.partition("/")
            preferred_models.setdefault(provider, set()).add(model_id)

    providers = build_profiles(
        models,
        provider_ref,
        existing_providers=existing_providers if isinstance(existing_providers, dict) else {},
        preferred_models=preferred_models,
        include_all_models=args.include_all_models,
    )

    new_creds = merge_credentials(creds if isinstance(creds, dict) else {}, refs)
    new_settings = merge_settings(settings if isinstance(settings, dict) else {}, providers)

    if args.dry_run:
        print("# Would write", creds_path)
        print(yaml.safe_dump(new_creds, sort_keys=False, allow_unicode=True), end="")
        print("# Would write", settings_path)
        print(yaml.safe_dump(new_settings, sort_keys=False, allow_unicode=True), end="")
        return 0

    dsh_home.mkdir(parents=True, exist_ok=True)
    creds_path.write_text(yaml.safe_dump(new_creds, sort_keys=False, allow_unicode=True), encoding="utf-8")
    settings_path.write_text(yaml.safe_dump(new_settings, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Updated {creds_path}")
    print(f"Updated {settings_path}")
    print("Providers:", ", ".join(sorted(providers)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
