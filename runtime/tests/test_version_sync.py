from __future__ import annotations

import re
import unittest
from pathlib import Path

from prumo_runtime import __version__
from prumo_runtime.workspace import semantic_version_key


class VersionSyncTests(unittest.TestCase):
    def test_runtime_version_matches_repo_metadata(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        pyproject_text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
        version_file = (repo_root / "VERSION").read_text(encoding="utf-8").strip()
        pyproject_match = re.search(r'^version = "([^"]+)"$', pyproject_text, re.MULTILINE)

        self.assertIsNotNone(pyproject_match)
        self.assertEqual(pyproject_match.group(1), __version__)
        self.assertEqual(version_file, __version__)


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
