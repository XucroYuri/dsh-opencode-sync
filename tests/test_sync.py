import json
import pathlib
import tempfile
import unittest

from dsh_opencode_sync import (
    build_profiles,
    collect_secrets,
    merge_credentials,
    merge_settings,
)

FIXTURE_OPENCODE = {
    "provider": {
        "zai-coding-plan": {
            "options": {"apiKey": "zai-key"},
        }
    },
}

FIXTURE_AUTH = {
    "deepseek": {"type": "api", "key": "ds-key"},
    "openai": {"type": "oauth", "access": "token"},
}

FIXTURE_MODELS = [
    ("zai-coding-plan/glm-5.3", {
        "name": "GLM-5.3",
        "api": {"url": "https://api.z.ai/api/coding/paas/v4", "npm": "@ai-sdk/openai-compatible"},
        "limit": {"context": 1000000, "output": 131072},
        "variants": {"high": {"effort": "high"}, "max": {"effort": "max"}},
    }),
    ("deepseek/deepseek-v4-pro", {
        "name": "DeepSeek V4 Pro",
        "api": {"url": "https://api.deepseek.com"},
        "limit": {"context": 1000000, "output": 384000},
    }),
]


class SyncTests(unittest.TestCase):
    def test_collect_secrets_skips_oauth(self):
        refs, provider_ref = collect_secrets(FIXTURE_OPENCODE, FIXTURE_AUTH)
        self.assertIn("DEEPSEEK_API_KEY", refs)
        self.assertIn("ZAI_CODING_PLAN_API_KEY", refs)
        self.assertNotIn("OPENAI_API_KEY", refs)
        self.assertIn("deepseek", provider_ref)

    def test_build_profiles(self):
        refs, provider_ref = collect_secrets(FIXTURE_OPENCODE, FIXTURE_AUTH)
        providers = build_profiles(FIXTURE_MODELS, provider_ref)
        self.assertIn("deepseek", providers)
        self.assertIn("zai-coding-plan", providers)
        self.assertEqual(providers["zai-coding-plan"]["api"], "openai-completions")
        # Known catalog routes omit models unless explicitly allowlisted.
        self.assertNotIn("models", providers["deepseek"])
        # Custom routes include models so they are serviceable.
        self.assertIn("models", providers["zai-coding-plan"])
        self.assertEqual(providers["zai-coding-plan"]["models"][0]["id"], "glm-5.3")

    def test_merge_preserves_existing(self):
        existing_settings = {
            "ui-onboarding": {"welcomeNoticeVersion": "x"},
            "llm-pi-ai": {"providers": {"opencode": {"apiKeyEnv": "OPENCODE_API_KEY"}}},
        }
        providers = {"deepseek": {"apiKeyEnv": "DEEPSEEK_API_KEY"}}
        merged = merge_settings(existing_settings, providers)
        self.assertEqual(merged["ui-onboarding"]["welcomeNoticeVersion"], "x")
        self.assertIn("opencode", merged["llm-pi-ai"]["providers"])
        self.assertIn("deepseek", merged["llm-pi-ai"]["providers"])

    def test_merge_credentials_adds_version(self):
        merged = merge_credentials({}, {"DEEPSEEK_API_KEY": "k"})
        self.assertEqual(merged["version"], 1)
        self.assertEqual(merged["refs"]["DEEPSEEK_API_KEY"], "k")


if __name__ == "__main__":
    unittest.main()
