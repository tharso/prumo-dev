"""#337 — a copy dos manifests não amarra o produto a um agente.

O card do plugin no Cowork dizia "Transforma o Claude em interface única…";
o manifest do Codex dizia "Transforma o Codex". O produto é agnóstico
(skills-first, #77) e a landing já dizia isso — os manifests ficaram pra
trás. Espírito do test_version_sync: N cópias da mesma verdade dessincronizam
em silêncio; o teste trava a sincronia E o conteúdo.

A mutação barata que este guard mata: reintroduzir copy por host
("Transforma o Claude/o Codex") em QUALQUER manifest.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PLUGIN_MANIFESTS = [
    REPO_ROOT / "plugin.json",
    REPO_ROOT / ".claude-plugin" / "plugin.json",
    REPO_ROOT / ".codex-plugin" / "plugin.json",
]

MARKETPLACE_MANIFESTS = [
    REPO_ROOT / "marketplace.json",
    REPO_ROOT / ".claude-plugin" / "marketplace.json",
]

# Amarração a agente único: "Transforma o Claude…", "transforma o Codex…".
BINDING_PATTERN = re.compile(r"[Tt]ransforma o (Claude|Codex)\b")


def _all_descriptions(data) -> list[str]:
    """Coleta recursivamente todo campo `description` de um JSON."""
    found: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "description" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_all_descriptions(value))
    elif isinstance(data, list):
        for item in data:
            found.extend(_all_descriptions(item))
    return found


class ManifestsCopyTests(unittest.TestCase):
    def test_plugin_manifests_compartilham_a_mesma_descricao(self):
        """Três cópias da mesma frase divergem em silêncio — trava a sincronia."""
        descricoes = {}
        for path in PLUGIN_MANIFESTS:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("description", data, f"description ausente em {path}")
            descricoes[str(path.relative_to(REPO_ROOT))] = data["description"]
        self.assertEqual(
            len(set(descricoes.values())), 1,
            f"descrições divergem entre manifests: {descricoes}",
        )

    def test_descricao_e_agnostica_de_agente(self):
        """Positivo E negativo: diz "qualquer agente" e não amarra a um host —
        sem o positivo, apagar a descrição passaria no negativo de graça."""
        data = json.loads(PLUGIN_MANIFESTS[0].read_text(encoding="utf-8"))
        descricao = data["description"]
        self.assertIn("qualquer agente", descricao)
        self.assertNotRegex(descricao, BINDING_PATTERN)

    def test_nenhum_manifest_amarra_o_produto_a_um_agente(self):
        """Varre TODO campo description de TODOS os manifests — inclusive os
        aninhados do marketplace (plugins[0]) e o top-level "via Claude"."""
        for path in PLUGIN_MANIFESTS + MARKETPLACE_MANIFESTS:
            data = json.loads(path.read_text(encoding="utf-8"))
            for descricao in _all_descriptions(data):
                rel = path.relative_to(REPO_ROOT)
                self.assertNotRegex(
                    descricao, BINDING_PATTERN,
                    f"{rel} amarra o produto a um agente: {descricao!r}",
                )
                self.assertNotIn(
                    "via Claude", descricao,
                    f"{rel} posiciona o produto 'via Claude': {descricao!r}",
                )


if __name__ == "__main__":
    unittest.main()
