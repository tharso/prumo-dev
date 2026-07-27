# Load Policy

> **module_version: 5.59.0**
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

1. **Perímetro automático:** por iniciativa própria, listar apenas as pastas do mapa do `Prumo/AGENT.md`. `Inbox4Mobile/` é listagem plana da própria pasta.
2. **Proibição por efeito, não por comando:** nenhuma enumeração recursiva ou ilimitada da raiz ou de pastas fora do mapa, por **qualquer** ferramenta (`find`, `ls -R`, `rg --files`, `tree`, glob `**/*`, APIs de filesystem). `node_modules`, `.git`, caches e builds ficam fora de qualquer listagem, em qualquer escopo.
3. **Escopo autorizado pela tarefa:** quando o usuário citar projeto ou caminho fora do mapa ("continuar o projeto X"), a expansão é dirigida e rasa — top-level do caminho citado, aprofundando só no rastro do alvo. Ambiguidade → perguntar o caminho, não explorar.
4. **Delegação leva o perímetro junto.** Subagente não herda módulo nenhum: o perímetro viaja **no prompt da delegação**, com os caminhos permitidos explícitos. Exemplo canônico:

   > Leia `Prumo/PAUTA.md` e `Prumo/REGISTRO.md` (apenas esses caminhos) e resuma os itens da seção Quente. Não liste nem explore nenhum outro diretório; se um caminho citado não existir, reporte em vez de procurar.

   Nunca delegar com "explore o workspace", "liste tudo" ou variações.

## Teto associativo

Sugestão associativa (conexão entre itens, ressurgência de esquecido) custa leitura além do mínimo. Vale o teto da regra 17 do core: no máximo **uma** por briefing, e nenhuma varredura pesada fora de ritual que a contrate explicitamente. Detalhe da regra em `prumo-core.md`.
