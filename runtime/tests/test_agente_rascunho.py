"""Caminho sancionado pro efêmero do agente (#263, P12 do relatório).

No Cowork com ponte de dispositivo, `rm` falha com `Operation not permitted`.
A #242 resolveu isso pro fluxo do usuário — quarentena `_to_delete/`, que ele
esvazia à mão. O que só ficou visível depois: **o agente também não consegue
limpar os próprios artefatos**, e cada tentativa de conserto deixa lixo na
quarentena DO USUÁRIO, obrigando o dono a garimpar o que ele descartou no meio
do que a máquina sujou.

O produto já tinha a resposta certa pra efêmero de máquina (`decidir_ephemeral`
→ `move-to-backup`, nunca `rm`). Faltava estendê-la ao rascunho do agente.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from prumo_runtime import sanitize
from prumo_runtime.fim import accumulation_signals

HOJE = date(2026, 7, 29)
VELHO = HOJE - timedelta(days=40)


class BaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "Prumo").mkdir(parents=True)
        self.rascunho = self.ws / ".prumo" / "state" / "rascunho"
        self.rascunho.mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def _envelhecer(self, path: Path, dias: int = 40) -> None:
        import os
        quando = (HOJE - timedelta(days=dias))
        stamp = __import__("time").mktime(quando.timetuple())
        os.utime(path, (stamp, stamp))

    def _arquivo(self, nome: str, dias: int = 40, conteudo: str = "x") -> Path:
        alvo = self.rascunho / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")
        self._envelhecer(alvo, dias)
        return alvo

    def _plano(self, rules=None) -> dict:
        return sanitize.build_plan(self.ws, today=HOJE, rules=rules)

    def _familias(self, plano: dict) -> dict[str, list[str]]:
        agrupado: dict[str, list[str]] = {}
        for item in plano["items"]:
            agrupado.setdefault(item["rule"], []).append(item["path"])
        return agrupado


class VarreduraTest(BaseTest):
    def test_rascunho_velho_vai_pro_backup_nunca_pro_rm(self) -> None:
        self._arquivo("reconstrucao.md")
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(familia, [".prumo/state/rascunho/reconstrucao.md"])
        acao = next(
            i["action"] for i in self._plano()["items"] if i["rule"] == "agente_rascunho"
        )
        self.assertEqual(acao, "move-to-backup", "rm não funciona sob a ponte do Cowork")

    def test_rascunho_novo_fica(self) -> None:
        """Negativa: efêmero é por IDADE, não por estar na pasta."""
        self._arquivo("de-hoje.md", dias=0)
        self.assertEqual(self._familias(self._plano()).get("agente_rascunho", []), [])

    def test_sem_filtro_de_sufixo(self) -> None:
        """Rascunho de agente é qualquer coisa — diferente do HTML/fonte do
        despacho. A cerca é o PATH exclusivo, não o sufixo."""
        for nome in ("a.md", "b.json", "c.txt", "d.sem-extensao"):
            self._arquivo(nome)
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(len(familia), 4, familia)

    def test_diretorio_e_movido_inteiro(self) -> None:
        """A unidade é o filho DIRETO: varrer arquivo a arquivo desmontaria
        uma reconstrução parcial e deixaria casca vazia (Codex, 263-5)."""
        self._arquivo("recon/parte-1.md")
        self._arquivo("recon/parte-2.md")
        self._envelhecer(self.rascunho / "recon")
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(familia, [".prumo/state/rascunho/recon"])

    def test_diretorio_com_arquivo_quente_nao_e_movido(self) -> None:
        """Negativa: um só arquivo novo segura a pasta inteira."""
        self._arquivo("recon/velho.md")
        self._arquivo("recon/agora.md", dias=0)
        self.assertEqual(self._familias(self._plano()).get("agente_rascunho", []), [])

    def test_pasta_ausente_e_zero_candidatos(self) -> None:
        """Criação é LAZY: o setup não pré-cria e ausência não é erro."""
        import shutil
        shutil.rmtree(self.rascunho)
        self.assertEqual(self._familias(self._plano()).get("agente_rascunho", []), [])


class SubtreeExclusivaTest(BaseTest):
    """Ordem de regra só garante disjunção quando todas rodam. Com `--rules`
    isolado, a MESMA coisa mudava de família e de ação — e num dos casos a
    ação era `delete` de verdade (Codex, 263-3)."""

    def test_handover_no_rascunho_nao_vira_handover_legacy(self) -> None:
        self._arquivo("HANDOVER-antigo.md")
        familias = self._familias(self._plano(rules=["handover_legacy"]))
        self.assertEqual(familias.get("handover_legacy", []), [])

    def test_handover_fora_do_rascunho_continua_sendo_pego(self) -> None:
        """Negativa: a exclusão é da subtree, não da família."""
        alvo = self.ws / ".prumo" / "state" / "HANDOVER-antigo.md"
        alvo.write_text("x", encoding="utf-8")
        familias = self._familias(self._plano(rules=["handover_legacy"]))
        self.assertTrue(familias.get("handover_legacy"))

    def test_fonte_duplicada_no_rascunho_nunca_e_deletada(self) -> None:
        """O pior caso: `asset_dedupe` faz DELETE de verdade."""
        vendored = self.ws / ".prumo" / "skills" / "decidir" / "assets" / "Boliand.otf"
        vendored.parent.mkdir(parents=True)
        vendored.write_bytes(b"fonte")
        alvo = self.rascunho / "Boliand.otf"
        alvo.write_bytes(b"fonte")
        self._envelhecer(alvo)

        for rules in (None, ["asset_dedupe"]):
            with self.subTest(rules=rules):
                familias = self._familias(self._plano(rules=rules))
                self.assertNotIn(
                    ".prumo/state/rascunho/Boliand.otf", familias.get("asset_dedupe", [])
                )


class PreservacaoPorCaminhoTest(BaseTest):
    """`_preserved` protegia por basename e por qualquer componente `logs`:
    um rascunho chamado `agent-lock.json` nunca seria limpo, contrariando
    "sem filtro" (Codex, 263-6)."""

    def test_nome_reservado_dentro_do_rascunho_e_limpo(self) -> None:
        self._arquivo("agent-lock.json")
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(familia, [".prumo/state/rascunho/agent-lock.json"])

    def test_pasta_logs_dentro_do_rascunho_e_limpa(self) -> None:
        self._arquivo("logs/saida.txt")
        self._envelhecer(self.rascunho / "logs")
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(familia, [".prumo/state/rascunho/logs"])

    def test_o_lock_canonico_continua_protegido(self) -> None:
        """Negativa: a preservação real não pode ter sido perdida."""
        lock = self.ws / ".prumo" / "state" / "agent-lock.json"
        lock.write_text("{}", encoding="utf-8")
        self._envelhecer(lock)
        todos = [i["path"] for i in self._plano()["items"]]
        self.assertNotIn(".prumo/state/agent-lock.json", todos)


class FimDetectaTest(BaseTest):
    """Sem entrar no `/fim`, rascunho envelheceria pra sempre sem NUNCA
    disparar a superfície que oferece a sanitize (Codex, 263-2)."""

    def test_rascunho_sozinho_dispara_sanitize(self) -> None:
        self._arquivo("velho.md")
        s = accumulation_signals(self.ws, today=HOJE)["signals"]
        self.assertEqual(s["rascunho_old"], 1)
        self.assertTrue(accumulation_signals(self.ws, today=HOJE)["suggest"]["sanitize"])

    def test_workspace_limpo_nao_sugere(self) -> None:
        s = accumulation_signals(self.ws, today=HOJE)
        self.assertEqual(s["signals"]["rascunho_old"], 0)
        self.assertFalse(s["suggest"]["sanitize"])


class ContratoTest(unittest.TestCase):
    def setUp(self) -> None:
        raiz = Path(__file__).resolve().parents[2]
        self.protecao = (raiz / "skills" / "prumo" / "references"
                         / "file-protection-rules.md").read_text(encoding="utf-8")
        self.porta = (raiz / "skills" / "prumo" / "references"
                      / "agent-md-template.md").read_text(encoding="utf-8")

    def test_a_porta_ensina_o_caminho(self) -> None:
        """Regra que depende de lembrar de abrir o manual já perdeu a briga:
        o gatilho tem de estar na superfície SEMPRE carregada (Codex, 263-1)."""
        self.assertIn("rascunho/", self.porta)
        self.assertIn("descartáveis", self.porta)

    def test_to_delete_e_so_do_usuario(self) -> None:
        linha = next(l for l in self.protecao.splitlines() if "`_to_delete/`" in l and "|" in l)
        self.assertIn("nunca subproduto ou rascunho do agente", linha)

    def test_rascunho_declara_o_carve_out_da_214(self) -> None:
        """Estende a #214 (o agente não escreve estado do runtime) em vez de
        revogá-la: aqui nada é fonte de verdade (Codex, 263-4)."""
        linha = next(
            l for l in self.protecao.splitlines()
            if l.startswith("| `.prumo/state/rascunho/`")
        )
        self.assertIn("#214", linha)
        self.assertIn("estende", linha)
        self.assertIn("descartável", linha)
        self.assertIn("LAZY", linha)


class AplicacaoDeVerdadeTest(BaseTest):
    """Etiqueta dizendo "vai pro backup" não é prova de que o caminhão chegou
    (Codex, r1). Estes rodam `apply_plan`."""

    def test_rascunho_sai_da_origem_e_chega_no_backup(self) -> None:
        alvo = self._arquivo("reconstrucao.md", conteudo="conteúdo do rascunho")
        plano = self._plano()
        sanitize.apply_plan(self.ws, plan=plano, today=HOJE)

        self.assertFalse(alvo.exists(), "o rascunho continua na origem")
        copias = list((self.ws / ".prumo" / "backups" / "sanitize").rglob("*reconstrucao.md"))
        self.assertTrue(copias, "nada chegou no backup")
        self.assertEqual(copias[0].read_text(encoding="utf-8"), "conteúdo do rascunho")

    def test_nada_de_rm_no_rascunho(self) -> None:
        """Sob a ponte do Cowork `rm` falha: se a ação virasse delete, o
        mecanismo inteiro deixaria de funcionar lá."""
        self._arquivo("qualquer.md")
        acoes = {i["action"] for i in self._plano()["items"] if i["rule"] == "agente_rascunho"}
        self.assertEqual(acoes, {"move-to-backup"})

    def test_isca_no_to_delete_fica_intocada(self) -> None:
        """A quarentena do usuário não entra em plano nenhum (#242/#263)."""
        isca = self.ws / "_to_delete" / "coisa-do-usuario.md"
        isca.parent.mkdir(parents=True)
        isca.write_text("decisão do dono", encoding="utf-8")
        self._envelhecer(isca, 400)

        plano = self._plano()
        self.assertEqual([i for i in plano["items"] if "_to_delete" in i["path"]], [])
        sanitize.apply_plan(self.ws, plan=plano, today=HOJE)
        self.assertTrue(isca.exists(), "a sanitize encostou na quarentena do usuário")


class PainelDoFimTest(BaseTest):
    """O JSON dizia `rascunho_old=1` e `suggest.sanitize=true` enquanto o
    painel mostrava tudo zero e caía no genérico "poeira técnica acumulada"
    (Codex, r1)."""

    def _texto(self) -> str:
        from prumo_runtime.commands.fim import _render_text
        return _render_text(accumulation_signals(self.ws, today=HOJE))

    def test_painel_conta_o_rascunho(self) -> None:
        self._arquivo("velho.md")
        self.assertIn("rascunhos do agente", self._texto())

    def test_recomendacao_cita_o_rascunho_quando_e_o_unico_sinal(self) -> None:
        """Citar só o que tem contagem > 0 é contrato do #179 PR10 — com o
        rascunho fora da lista, a recomendação virava genérica."""
        self._arquivo("velho.md")
        texto = self._texto()
        self.assertIn("1 rascunhos do agente", texto)

    def test_painel_limpo_mostra_zero_sem_inventar(self) -> None:
        """Negativa: sem rascunho, o campo aparece zerado e nada é sugerido."""
        texto = self._texto()
        self.assertIn("rascunhos do agente (>14d): 0", texto)


class RegraDeOuroTest(BaseTest):
    """Mover INTEIRO um rascunho que carrega `backups/` criaria backup dentro
    de backup — a regra de ouro da #178 (Codex, r2)."""

    def test_arvore_com_backups_fica_onde_esta(self) -> None:
        self._arquivo("recon/backups/copia.md")
        self._arquivo("recon/nota.md")
        self._envelhecer(self.rascunho / "recon" / "backups")
        self._envelhecer(self.rascunho / "recon")

        plano = self._plano()
        familia = self._familias(plano).get("agente_rascunho", [])
        self.assertEqual(familia, [], "moveu árvore que carrega backup")

        sanitize.apply_plan(self.ws, plan=plano, today=HOJE)
        aninhado = list((self.ws / ".prumo" / "backups" / "sanitize").rglob("backups"))
        self.assertEqual(aninhado, [], "backup dentro de backup")

    def test_arvore_sem_backups_continua_saindo(self) -> None:
        """Negativa: a recusa é do vetor, não da funcionalidade."""
        self._arquivo("recon/nota.md")
        self._envelhecer(self.rascunho / "recon")
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(familia, [".prumo/state/rascunho/recon"])


class ExclusividadeNoFimTest(BaseTest):
    """A exclusão aplicada só no `build_plan` não corrigia o painel: o `/fim`
    consome `iter_handover_files` direto (Codex, r2)."""

    def test_handover_no_rascunho_nao_conta_como_legado(self) -> None:
        self._arquivo("HANDOVER-x.md", dias=0)  # recente: só o handover contaria
        s = accumulation_signals(self.ws, today=HOJE)["signals"]
        self.assertEqual(s["handover_legacy"], 0, "rascunho disparou handover_legacy no painel")

    def test_handover_velho_no_rascunho_conta_uma_familia_so(self) -> None:
        self._arquivo("HANDOVER-y.md")
        s = accumulation_signals(self.ws, today=HOJE)["signals"]
        self.assertEqual(s["handover_legacy"], 0)
        self.assertEqual(s["rascunho_old"], 1)

    def test_handover_fora_do_rascunho_continua_contando(self) -> None:
        """Negativa: a exclusão é da subtree, não da família."""
        alvo = self.ws / ".prumo" / "state" / "HANDOVER-z.md"
        alvo.write_text("x", encoding="utf-8")
        s = accumulation_signals(self.ws, today=HOJE)["signals"]
        self.assertEqual(s["handover_legacy"], 1)


class ContratoDaSanitizeTest(unittest.TestCase):
    """Sem runtime, o `/fim` encaminha pro manual — que precisa saber executar
    a família nova (Codex, r2)."""

    def test_a_tabela_canonica_conhece_a_familia(self) -> None:
        raiz = Path(__file__).resolve().parents[2]
        doc = (raiz / "skills" / "prumo" / "references" / "modules"
               / "sanitize.md").read_text(encoding="utf-8")
        linha = next(l for l in doc.splitlines() if "`agente_rascunho`" in l)
        self.assertIn("move → backup", linha)
        self.assertIn("exclusiva", linha)
        self.assertIn("inteiro", linha)


class ArvoreInteiraFriaTest(BaseTest):
    """"Árvore inteira fria" checava só os ARQUIVOS descendentes. Uma
    reconstrução criada hoje com arquivos antigos dentro — um `mv` basta — era
    considerada fria e saía inteira, tirando trabalho ativo do rascunho
    (Codex, r3)."""

    def test_diretorio_raiz_quente_segura_a_arvore(self) -> None:
        self._arquivo("recon/velho.md")          # arquivo antigo
        # o diretório em si é de agora (mtime não envelhecido)
        self.assertEqual(self._familias(self._plano()).get("agente_rascunho", []), [])

    def test_subdiretorio_quente_segura_a_arvore(self) -> None:
        self._arquivo("recon/sub/velho.md")
        self._envelhecer(self.rascunho / "recon")
        # `recon/sub` continua com mtime de agora
        self.assertEqual(self._familias(self._plano()).get("agente_rascunho", []), [])

    def test_arvore_toda_fria_sai(self) -> None:
        """Negativa: a exigência não pode travar o caso legítimo."""
        self._arquivo("recon/sub/velho.md")
        self._envelhecer(self.rascunho / "recon" / "sub")
        self._envelhecer(self.rascunho / "recon")
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(familia, [".prumo/state/rascunho/recon"])


class BordasDaArvoreTest(BaseTest):
    """Duas bordas da própria regra "árvore inteira fria" (Codex, r4)."""

    def test_pasta_vazia_fria_sai(self) -> None:
        """Exigir arquivos fazia carcaça vazia nunca sair."""
        vazia = self.rascunho / "carcaca"
        vazia.mkdir()
        self._envelhecer(vazia)
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(familia, [".prumo/state/rascunho/carcaca"])

    def test_arvore_so_de_pastas_vazias_frias_sai(self) -> None:
        alvo = self.rascunho / "casca" / "dentro"
        alvo.mkdir(parents=True)
        self._envelhecer(alvo)
        self._envelhecer(self.rascunho / "casca")
        familia = self._familias(self._plano()).get("agente_rascunho", [])
        self.assertEqual(familia, [".prumo/state/rascunho/casca"])

    def test_pasta_vazia_quente_fica(self) -> None:
        """Negativa: vazia não é sinônimo de descartável — idade ainda manda."""
        (self.rascunho / "de-hoje").mkdir()
        self.assertEqual(self._familias(self._plano()).get("agente_rascunho", []), [])

    def test_filho_chamado_backups_nunca_e_movido(self) -> None:
        """O próprio filho direto com nome de backup ia pra dentro do backup."""
        alvo = self.rascunho / "backups"
        alvo.mkdir()
        (alvo / "coisa.md").write_text("x", encoding="utf-8")
        self._envelhecer(alvo / "coisa.md")
        self._envelhecer(alvo)

        plano = self._plano()
        self.assertEqual(self._familias(plano).get("agente_rascunho", []), [])
        sanitize.apply_plan(self.ws, plan=plano, today=HOJE)
        aninhado = list((self.ws / ".prumo" / "backups" / "sanitize").rglob("backups"))
        self.assertEqual(aninhado, [], "backup dentro de backup")


class DeteccaoAlinhadaComExecucaoTest(BaseTest):
    """Symlink na árvore faz o `build_plan` recusar. Se o iterator contasse
    assim mesmo, o `/fim` recomendaria sanitize pra sempre e a sanitize
    produziria plano vazio (Codex, r5)."""

    def test_arvore_com_symlink_nao_conta_no_fim(self) -> None:
        self._arquivo("recon/nota.md")
        (self.rascunho / "recon" / "atalho").symlink_to(self.ws / "Prumo")
        self._envelhecer(self.rascunho / "recon")

        s = accumulation_signals(self.ws, today=HOJE)["signals"]
        self.assertEqual(s["rascunho_old"], 0, "alarme sem incêndio apagável")

    def test_o_que_o_fim_conta_a_sanitize_consegue_apagar(self) -> None:
        """A propriedade geral: detecção e execução não podem divergir."""
        self._arquivo("com-link/nota.md")
        (self.rascunho / "com-link" / "atalho").symlink_to(self.ws / "Prumo")
        self._envelhecer(self.rascunho / "com-link")
        self._arquivo("limpo/nota.md")
        self._envelhecer(self.rascunho / "limpo")

        contados = accumulation_signals(self.ws, today=HOJE)["signals"]["rascunho_old"]
        planejados = len(self._familias(self._plano()).get("agente_rascunho", []))
        self.assertEqual(contados, planejados)
        self.assertEqual(planejados, 1, "o limpo tem de sair")


if __name__ == "__main__":
    unittest.main()
