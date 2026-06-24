"""Guards de conteúdo do aviso de versão no fluxo manual (sem runtime). Issue #106.

Não dá para simular um agente obediente num unittest, mas dá para impedir que o
texto volte a ficar ambíguo — foi a ambiguidade (Passo 2 com cara de "fonte
disponível" + "Nunca use WebFetch" grande demais) que fez a comparação remota ser
pulada, produzindo um falso "sem drift" mesmo com versão nova publicada.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_VERSION_URL = "raw.githubusercontent.com/tharso/prumo/main/VERSION"


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


class VersionWarnManualGuards(unittest.TestCase):
    def test_version_update_authorizes_remote_fetch_for_comparison(self):
        text = _read("skills/prumo/references/modules/version-update.md")
        self.assertIn(RAW_VERSION_URL, text)
        # Buscar o VERSION remoto via WebFetch para COMPARAÇÃO é permitido.
        self.assertIn("WebFetch", text)
        self.assertIn("permitido", text)
        self.assertRegex(text, r"compar(ar|ação)")

    def test_version_update_scopes_prohibition_to_core_rewrite(self):
        text = _read("skills/prumo/references/modules/version-update.md")
        # A proibição de WebFetch é escopada a aplicar update / reescrever o core,
        # não à comparação de versão.
        self.assertIn("reescrever", text)
        self.assertIn("PRUMO-CORE.md", text)

    def test_version_update_requires_warning_when_cannot_fetch(self):
        text = _read("skills/prumo/references/modules/version-update.md")
        # Sem nenhum jeito de buscar: avisar; nunca declarar "sem drift" sem comparar.
        self.assertIn("Não consegui checar a versão pública", text)
        # Rigor: exige a PROIBIÇÃO ("Nunca ... sem drift"), não só o termo solto.
        self.assertRegex(text, r"[Nn]unca[^\n]*sem drift")

    def test_briefing_entrypoints_mention_remote_comparison(self):
        proc = _read("skills/prumo/references/modules/briefing-procedure.md")
        self.assertIn("comparação remota", proc)
        skill = _read("skills/briefing/SKILL.md")
        self.assertIn(RAW_VERSION_URL, skill)


if __name__ == "__main__":
    unittest.main()
