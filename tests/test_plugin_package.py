import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PluginPackageContractTest(unittest.TestCase):
    def test_marketplaces_resolve_declared_plugin_payloads(self) -> None:
        for client in ("claude", "codex"):
            marketplace_path = ROOT / f".{client}-plugin" / "marketplace.json"
            marketplace = json.loads(marketplace_path.read_text())
            entry = marketplace["plugins"][0]
            source = ROOT / entry["source"]
            manifest_path = source / f".{client}-plugin" / "plugin.json"

            self.assertTrue(manifest_path.is_file(), manifest_path)
            manifest = json.loads(manifest_path.read_text())
            skills = source / manifest["skills"]
            self.assertTrue(skills.is_dir(), skills)
            self.assertEqual(
                {path.parent.name for path in skills.glob("*/SKILL.md")},
                {"review-docs", "write-docs"},
            )

            for key in ("skills", "hooks"):
                if declared_path := manifest.get(key):
                    self.assertTrue((source / declared_path).exists(), declared_path)


if __name__ == "__main__":
    unittest.main()
