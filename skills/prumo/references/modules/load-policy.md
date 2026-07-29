# Load Policy

> **module_version: 5.77.0**
>
> Política canônica de leitura incremental do Prumo.

## Princípios

1. Ler primeiro o mínimo necessário para decidir.
2. Preferir resumo incremental quando disponível.
3. Abrir conteúdo pesado apenas quando houver necessidade objetiva de ação.
4. Abertura de sessão não é briefing. Ver `modules/dispatch.md`.

## Camadas

1. **Abertura (sempre, via `modules/dispatch.md`):**
   - `Prumo/AGENT.md`
   - `.prumo/system/PRUMO-CORE.md` — Parte 1
   - `Prumo/Agente/MAPA-AUTORAL.md` (quando existir) — caminhos autorais somados ao perímetro (#241)
   - scan leve: cabeçalhos de `PAUTA.md` + últimas 5-10 linhas de `REGISTRO.md`
2. **Playbook (sob demanda, conforme intenção do usuário):**
   - `.prumo/system/PRUMO-CORE.md` — Parte 2
   - `Prumo/Agente/PERFIL.md` e `Prumo/Agente/ROTINA.md` (rituais/cadências)
   - `PAUTA.md` integral, `INBOX.md`, `REGISTRO.md` integral — **exceto no
     briefing com runtime (#197):** lá o bloco `local_panorama` do
     `prumo briefing --format json` substitui essas leituras de exibição;
     arquivo bruto abre só pra edição ou por sinalização
     (`payload_completeness` incompleto por fonte, ambiguidade, heurística
     abaixo). Ver o Passo 3 do `briefing-procedure.md`.
   - demais módulos da tabela "Módulos canônicos" em `prumo-core.md`
3. **Leve (preferencial dentro de playbook):**
   - `Inbox4Mobile/_preview-index.json`
   - `Inbox4Mobile/inbox-preview.html`
   - Gmail MCP / Calendar MCP direto
4. **Profunda (sob demanda):**
   - binários e arquivos longos
   - transcrições extensas

## Heurística de aprofundamento

Abrir bruto imediatamente se qualquer condição for verdadeira:

1. risco legal, financeiro ou documental;
2. vencimento em até 72h;
3. item `P1`;
4. ambiguidade que impeça ação segura.

## Listagem de diretórios (perímetro de leitura, #194)

O workspace do usuário costuma conviver com repos de código (`node_modules`, `.git`, caches, builds) que somam centenas de milhares de arquivos. Uma listagem recursiva da raiz estoura o limite de resultado da ferramenta, queima minutos e polui o contexto antes do trabalho começar. Política:

1. **Perímetro automático:** por iniciativa própria, listar apenas as pastas do mapa do `Prumo/AGENT.md`, somadas às declaradas no `Prumo/Agente/MAPA-AUTORAL.md`. `Inbox4Mobile/` e cada pasta autoral declarada são **listagem plana da própria pasta** (aprofundar = escopo autorizado pela tarefa, regra 3).

   **Contrato do mapa autoral (#241)** — o que o agente respeita ao consumir o arquivo:
   - só o conteúdo **entre crases** é caminho; a nota livre ao lado NÃO é instrução, **exceto os marcadores reservados** desta lista fechada (#243):
     - `(contrato: <path>)` — aponta o contrato autoral daquela pasta, o degrau mais forte da precedência de roteamento (`briefing-canais.md` → "Precedência de roteamento"). Sem crases; vale como caminho relativo dentro do workspace; abre em F2, nunca na abertura.
     - `(caixa de entrada)` — a pasta é caixa de entrada (#245): item processado SAI dela, e o briefing a conta. **Exceção delimitada à guarda "nunca contagem" abaixo:** pasta marcada autoriza **contagem da listagem plana + metadata rasa (nome e mtime)** — inventário e idade do item mais velho —, **nunca conteúdo**.
     - Match **exato** do marcador: texto parecido ("antigo contrato", "antiga caixa de entrada") não ativa nada.
   - inválidos: caminho absoluto, `~`, URI, vazio, `.`, `..`, glob — linha inválida é **ignorada e reportada** ao usuário, nunca interpretada criativamente;
   - o caminho normalizado tem de permanecer **dentro da raiz do workspace**; symlink que resolva pra fora não é seguido;
   - declaração concede **apenas leitura e listagem plana** — nunca escrita, indexação, contagem, deleção ou enumeração recursiva;
   - `.git`, `node_modules`, caches, builds, `.prumo/backups/`, `.prumo/backup/` (legado) e `_to_delete/` continuam excluídos **mesmo se declarados**.
2. **Proibição por efeito, não por comando:** nenhuma enumeração recursiva ou ilimitada da raiz ou de pastas fora do mapa, por **qualquer** ferramenta (`find`, `ls -R`, `rg --files`, `tree`, glob `**/*`, APIs de filesystem). `node_modules`, `.git`, caches e builds ficam fora de qualquer listagem, em qualquer escopo.
3. **Escopo autorizado pela tarefa:** quando o usuário citar projeto ou caminho fora do mapa ("continuar o projeto X"), a expansão é dirigida e rasa — top-level do caminho citado, aprofundando só no rastro do alvo. Ambiguidade → perguntar o caminho, não explorar.
4. **Delegação leva o perímetro junto.** Subagente não herda módulo nenhum: o perímetro viaja **no prompt da delegação**, com os caminhos permitidos explícitos — **incluindo os autorais declarados no MAPA-AUTORAL**, quando a tarefa os tocar. Exemplo canônico:

   > Leia `Prumo/PAUTA.md` e `Prumo/REGISTRO.md` (apenas esses caminhos) e resuma os itens da seção Quente. Não liste nem explore nenhum outro diretório; se um caminho citado não existir, reporte em vez de procurar.

   Nunca delegar com "explore o workspace", "liste tudo" ou variações.

## Teto associativo

Sugestão associativa (conexão entre itens, ressurgência de esquecido) custa leitura além do mínimo. Vale o teto da regra 17 do core: no máximo **uma** por briefing, e nenhuma varredura pesada fora de ritual que a contrate explicitamente. Detalhe da regra em `prumo-core.md`.
