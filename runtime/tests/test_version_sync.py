from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from prumo_runtime import __version__
from prumo_runtime.workspace import semantic_version_key


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_pyproject_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    if not match:
        raise AssertionError(f"version field not found in {path}")
    return match.group(1)


def _read_version_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _read_json_top_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "version" not in data:
        raise AssertionError(f"top-level 'version' not found in {path}")
    return data["version"]


def _read_marketplace_plugin_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    plugins = data.get("plugins") or []
    if not plugins or "version" not in plugins[0]:
        raise AssertionError(f"plugins[0].version not found in {path}")
    return plugins[0]["version"]


def _read_md_header_version(path: Path, label: str) -> str:
    """
    Lê headers como `> **prumo_version: X.Y.Z**` ou `> **module_version: X.Y.Z**`.
    `label` é o nome (`prumo_version` ou `module_version`).
    """
    text = path.read_text(encoding="utf-8")
    pattern = rf"\*\*{re.escape(label)}:\s*([0-9][^\s*]*)\*\*"
    match = re.search(pattern, text)
    if not match:
        raise AssertionError(f"header '{label}' not found in {path}")
    return match.group(1)


def _read_readme_version(path: Path) -> str:
    """Extrai versão da linha em backticks após '## Versão' no README."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## Versão\s*\n+`([^`]+)`", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"'## Versão' section with backtick version not found in {path}")
    return match.group(1)


# Lista canônica das fontes de versão do Prumo. Decisão registrada em
# `gotchas.md` (seção "Versoes fora de sincronia"): todos os 11 lugares
# devem casar — runtime, manifestos distribuídos e headers de skills
# canônicas. Quando o produto bumpar versão, todos sobem juntos.
#
# Cada entrada é `(nome humano, caminho, função extratora)`.
VERSION_SOURCES: list[tuple[str, Path, callable]] = [
    ("VERSION (raiz)", REPO_ROOT / "VERSION", _read_version_file),
    ("pyproject.toml", REPO_ROOT / "pyproject.toml", _read_pyproject_version),
    ("plugin.json (raiz)", REPO_ROOT / "plugin.json", _read_json_top_version),
    (
        "marketplace.json (raiz, plugins[0].version)",
        REPO_ROOT / "marketplace.json",
        _read_marketplace_plugin_version,
    ),
    (
        ".claude-plugin/plugin.json",
        REPO_ROOT / ".claude-plugin" / "plugin.json",
        _read_json_top_version,
    ),
    (
        ".claude-plugin/marketplace.json (plugins[0].version)",
        REPO_ROOT / ".claude-plugin" / "marketplace.json",
        _read_marketplace_plugin_version,
    ),
    (
        ".codex-plugin/plugin.json",
        REPO_ROOT / ".codex-plugin" / "plugin.json",
        _read_json_top_version,
    ),
    (
        "skills/prumo/references/prumo-core.md (prumo_version)",
        REPO_ROOT / "skills" / "prumo" / "references" / "prumo-core.md",
        lambda p: _read_md_header_version(p, "prumo_version"),
    ),
    (
        "skills/prumo/references/modules/dispatch.md (module_version)",
        REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "dispatch.md",
        lambda p: _read_md_header_version(p, "module_version"),
    ),
    (
        "skills/prumo/references/modules/load-policy.md (module_version)",
        REPO_ROOT / "skills" / "prumo" / "references" / "modules" / "load-policy.md",
        lambda p: _read_md_header_version(p, "module_version"),
    ),
    (
        "README.md (seção ## Versão)",
        REPO_ROOT / "README.md",
        _read_readme_version,
    ),
]
# .codex-plugin/marketplace.json é deliberadamente excluído: o schema do
# Codex não prevê campo `version` no marketplace. Documentado em gotchas.md.


class VersionSyncTests(unittest.TestCase):
    def test_all_canonical_sources_match_runtime_version(self) -> None:
        """Todas as 11 fontes canônicas devem casar com `prumo_runtime.__version__`.

        Lista expandida em #83 (audit Codex em #81 P1.3) cobrindo manifestos
        `.claude-plugin/`, `.codex-plugin/` e headers de skills canônicas.
        """
        for label, path, extract in VERSION_SOURCES:
            with self.subTest(source=label):
                actual = extract(path)
                self.assertEqual(
                    actual,
                    __version__,
                    f"{label} declara '{actual}', runtime declara '{__version__}'",
                )

    def test_codex_marketplace_does_not_carry_version_by_design(self) -> None:
        """Documenta a exceção: `.codex-plugin/marketplace.json` não tem `version`.

        O schema do Codex não prevê o campo. Se um dia ele for adicionado, este
        teste deve ser removido e o arquivo entra em VERSION_SOURCES.
        """
        path = REPO_ROOT / ".codex-plugin" / "marketplace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertNotIn(
            "version",
            data,
            "schema do Codex não prevê 'version' no marketplace; se isso mudou, atualize VERSION_SOURCES",
        )
        # Também garante que o primeiro plugin não tem version no item
        plugins = data.get("plugins") or []
        if plugins:
            self.assertNotIn(
                "version",
                plugins[0],
                "schema do Codex não prevê 'version' nos itens; se isso mudou, atualize VERSION_SOURCES",
            )


class SemanticVersionKeyTests(unittest.TestCase):
    """Parser tolerante usado pra detectar drift entre core do workspace e runtime.

    Não é semver completo. Só cobre major.minor.patch com tolerância a prefixos
    (v5.1.1) e lixo (cai em (0,)). Pre-release e build metadata não são tratados
    como caso especial — viram dígito extra no fim da tupla, o que faz "5.1.1-rc1"
    parecer MAIOR que "5.1.1" e não menor. Essa limitação está documentada abaixo
    e deve ser consertada só se o Prumo passar a distribuir pre-releases.
    """

    def test_parses_basic_semver(self) -> None:
        self.assertEqual(semantic_version_key("5.1.1"), (5, 1, 1))

    def test_orders_correctly_across_patch_levels(self) -> None:
        self.assertLess(semantic_version_key("5.1.0"), semantic_version_key("5.1.1"))
        self.assertLess(semantic_version_key("5.1.1"), semantic_version_key("5.1.2"))

    def test_two_digit_minor_orders_numerically_not_lexically(self) -> None:
        # "5.10.0" > "5.2.0" numericamente. Se o parser fizesse comparação de string
        # em vez de tupla de int, essa asserção falharia (string "5.10" < "5.2").
        self.assertGreater(
            semantic_version_key("5.10.0"),
            semantic_version_key("5.2.0"),
        )

    def test_major_bump_beats_any_minor_patch(self) -> None:
        self.assertGreater(
            semantic_version_key("6.0.0"),
            semantic_version_key("5.99.99"),
        )

    def test_empty_string_falls_back_to_zero_tuple(self) -> None:
        self.assertEqual(semantic_version_key(""), (0,))

    def test_garbage_string_falls_back_to_zero_tuple(self) -> None:
        self.assertEqual(semantic_version_key("foo"), (0,))

    def test_prefix_is_stripped(self) -> None:
        self.assertEqual(semantic_version_key("v5.1.1"), semantic_version_key("5.1.1"))

    def test_short_form_compares_less_than_full_form(self) -> None:
        # "5.1" vira (5, 1). "5.1.0" vira (5, 1, 0). Pela ordem lexicográfica
        # de tuplas do Python, (5, 1) < (5, 1, 0). Comportamento aceitável pro
        # Prumo porque quem escreve "5.1" em PRUMO-CORE.md está ou errado ou
        # desatualizado — drift-forward é seguro. Documentado pra não surpreender.
        self.assertLess(
            semantic_version_key("5.1"),
            semantic_version_key("5.1.0"),
        )

    def test_pre_release_suffix_is_treated_as_extra_digit(self) -> None:
        # LIMITAÇÃO: "5.1.1-rc1" vira (5, 1, 1, 1) porque o parser só coleta dígitos
        # e ignora separadores. Resultado: pre-release parece MAIOR que release.
        # Não é bug crítico enquanto o Prumo não publicar tags -rc/-beta. Se mudar,
        # trocar pelo módulo `packaging.version` ou equivalente.
        self.assertGreater(
            semantic_version_key("5.1.1-rc1"),
            semantic_version_key("5.1.1"),
        )

    def test_build_metadata_is_treated_as_extra_digit(self) -> None:
        # Mesma limitação de pre-release. "5.1.1+build.1" → (5, 1, 1, 1).
        self.assertGreater(
            semantic_version_key("5.1.1+build.1"),
            semantic_version_key("5.1.1"),
        )


if __name__ == "__main__":
    unittest.main()
