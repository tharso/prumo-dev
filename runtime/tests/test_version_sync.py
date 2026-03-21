from __future__ import annotations

import re
import unittest
from pathlib import Path

from prumo_runtime import __version__


class VersionSyncTests(unittest.TestCase):
    def test_runtime_version_matches_repo_metadata(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        pyproject_text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
        version_file = (repo_root / "VERSION").read_text(encoding="utf-8").strip()
        pyproject_match = re.search(r'^version = "([^"]+)"$', pyproject_text, re.MULTILINE)

        self.assertIsNotNone(pyproject_match)
        self.assertEqual(pyproject_match.group(1), __version__)
        self.assertEqual(version_file, __version__)


if __name__ == "__main__":
    unittest.main()
