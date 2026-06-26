# Verbos do acervo

O `acervo` não tem allowlist por item (como o `decidir`): são sempre **três
verbos fixos**. O foco é garimpar o limbo — resgatar, atacar ou descartar o que
ficou parado.

| Verbo | `verb` (token) | Tom | Confirma antes? | O que faz |
|-------|----------------|-----|-----------------|-----------|
| Incluir na pauta | `include_pauta` | verde | não | Vira entrada acionável na `PAUTA.md` (seção `Horizonte` por padrão). |
| Atacar agora | `attack_now` | azul | não | O agente trabalha o item na sessão (desenvolver ideia, começar tarefa). |
| Excluir | `delete` | vermelho | **sim** | **Arquiva** (move pra `Prumo/Arquivo/Acervo/` + registro). Deleção permanente só sob pedido explícito. |

## Camadas de execução

**Direto (sem nova confirmação):**

- `include_pauta` — anexar à `PAUTA.md`. O comentário pode dirigir a seção e o
  prazo (`| cobrar: DD/MM`).
- `attack_now` — começar o trabalho. É julgamento do agente, não mecânica.

**Confirma antes (ASSERT do core — nada some no escuro):**

- `delete` — toda remoção de conteúdo do usuário confirma o plano e registra no
  `REGISTRO.md` antes de tocar o original. O Prumo nunca deleta: **arquiva**.

## Contrato de proveniência (remoção segura)

Cada item do relatório carrega:

- `source_kind` — `ideia` | `pauta_hibernando` | `referencia`
- `source_path` — caminho relativo ao workspace (sempre dentro de `Prumo/`)
- `anchor` — seção/heading (fragmentos) ou nome do arquivo (referências)
- `line_start` / `line_end` — intervalo do fragmento (null para arquivo inteiro)
- `content_hash` — hash normalizado do trecho (fragmento) ou dos bytes (arquivo)

**Na hora de excluir:**

1. Reabrir `source_path`, localizar o item pela `anchor`/linhas.
2. Recalcular o hash e **comparar com `content_hash`**.
3. **Bloquear e pedir revisão** se: o hash divergir (arquivo mudou desde a
   geração), o trecho aparecer em **mais de um lugar**, o `source_path` tentar
   **escapar de `Prumo/`**, ou o arquivo **não existir**.
4. Arquivos **operacionais** de `Referencias/` (`INDICE.md`,
   `EMAIL-CURADORIA.md`, `WORKFLOWS.md`) são **inapagáveis** — nem entram no
   acervo, e a remoção recusa por garantia dupla.
5. `delete` **sem registro prévio** no `REGISTRO.md` **falha**.

O runtime implementa essas travas: `prumo acervo --workspace <ws> apply
--report <arquivo.json>` (read-modify seguro; `--permanent` só sob pedido
explícito do usuário).

## Por que não há "guardar"/"virar referência"

O acervo já É o lugar das referências guardadas. Reguardar seria buraco negro
(o anti-padrão que a `decidir` matou em #109/#110). Se um item merece virar
referência viva, isso é `include_pauta` com destino, não acúmulo passivo.
