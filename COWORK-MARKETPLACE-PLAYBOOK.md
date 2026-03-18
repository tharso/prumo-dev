# Cowork Marketplace Plugin Install Playbook

Este documento consolida lições práticas para fazer plugin instalar via marketplace no Cowork Desktop (sem depender de upload manual `.zip`) e manter update previsível para usuário comum.

Serve como base para copiar em outro projeto.

## 1) Resumo executivo (o que realmente quebra)

Se você só ler uma parte, leia esta.

1. Marketplace por URL `raw` pode sincronizar e ainda falhar na instalação.
2. `source` relativo no marketplace (`./algo`) é frágil para fluxo por URL `raw`.
3. Se `marketplace.name` e `plugin.name` forem iguais, há risco de recursão de cache (`ENAMETOOLONG`).
4. Se marketplace e plugin manifest declararem componentes ao mesmo tempo, ocorre conflito de manifest.
5. Se o pacote distribuído tiver dois `plugin.json` com o mesmo `name`, o discovery de slash command pode ficar inconsistente no app.
6. O erro visual no app costuma ser genérico. A causa real aparece nos logs do desktop.
7. Se a sessão/chat foi aberta antes da instalação do plugin, o slash command pode continuar "desconhecido" nessa sessão mesmo após instalar.

## 2) Causas raiz encontradas neste caso

### Causa A: `source` relativo com marketplace URL raw

- Sintoma: sync funciona, instalar falha com `Source path does not exist`.
- Motivo: no fluxo por URL raw, o cache do marketplace pode virar arquivo JSON local (não árvore de diretórios esperada para `./cowork-plugin`).

### Causa B: slug igual entre marketplace e plugin

- Sintoma: instalação até inicia, depois estoura `ENAMETOOLONG` com path recursivo.
- Motivo: colisão de nomes em cache (`.../cache/<marketplace>/<plugin>/<version>/...`) gerando nesting repetido.

### Causa C: conflito de componentes entre marketplace e plugin manifest

- Sintoma: plugin instala, mas aparece erro de conflito de manifest.
- Motivo: marketplace entry define componentes com `strict: false` e o `plugin.json` também define componentes.

### Causa D: manifesto de plugin duplicado no mesmo pacote

- Sintoma: skill funciona por invocação interna, mas slash command não aparece no autocomplete ou retorna "comando desconhecido".
- Motivo: pacote com múltiplos `plugin.json` para o mesmo plugin (`name` igual), com bases de paths diferentes, pode gerar source of truth ambígua no discovery do frontend.

### Causa E: sessão iniciada sem plugin carregado

- Sintoma: `/plugin:comando` retorna "comando desconhecido" em uma conversa, mas funciona em outra.
- Motivo: a lista de slash commands é montada no `init` da sessão. Se o plugin foi instalado depois, a sessão antiga pode continuar sem o comando até abrir sessão nova (ou reinit efetivo).

## 3) Padrão seguro recomendado (copiar e adaptar)

### Marketplace (`marketplace.json` e `.claude-plugin/marketplace.json`)

- `name`: use slug distinto do plugin (ex.: `meu-plugin-marketplace`).
- entry do plugin:
  - `name`: slug do plugin (ex.: `meu-plugin`).
  - `source`: objeto remoto (`url` git + `ref`) em vez de path relativo.
  - `strict: true`.
  - não declarar `skills`/`commands`/`agents` no marketplace entry quando o `plugin.json` já declara.

Exemplo:

```json
{
  "name": "meu-plugin-marketplace",
  "owner": { "name": "Maintainers" },
  "plugins": [
    {
      "name": "meu-plugin",
      "source": {
        "source": "url",
        "url": "https://github.com/ORG/REPO.git",
        "ref": "main"
      },
      "version": "1.2.3",
      "description": "Plugin X",
      "author": { "name": "Maintainers" },
      "license": "MIT",
      "strict": true
    }
  ]
}
```

### Plugin manifest (`plugin.json`, `.claude-plugin/plugin.json`, e pacote runtime)

- Centralize componentes aqui (skills/commands/agents).
- Mantenha o mesmo contrato entre raiz e `.claude-plugin/` para compatibilidade de origem.
- Evite manifesto duplicado dentro do subdiretório de runtime (`cowork-plugin/plugin.json`) se ele descreve o mesmo plugin.

Exemplo:

```json
{
  "name": "meu-plugin",
  "version": "1.2.3",
  "description": "Plugin X",
  "author": { "name": "Maintainers" },
  "license": "MIT",
  "skills": [
    "./skills/core",
    "./skills/briefing"
  ]
}
```

## 4) O que fazer e o que não fazer

### Faça

- Use `source` remoto por objeto (`url` git + `ref`) no marketplace.
- Use `marketplace.name` diferente de `plugin.name`.
- Use `strict: true` no marketplace entry se componentes estão no `plugin.json`.
- Versione de forma consistente:
  - `VERSION`
  - `cowork-plugin/VERSION`
  - `plugin.json` (raiz)
  - `.claude-plugin/plugin.json`
- Inclua `.claude-plugin/marketplace.json` e `.claude-plugin/plugin.json` para compatibilidade com add por URL de repositório.
- Depois de instalar/atualizar plugin, teste em conversa nova (sessão nova) antes de concluir que "não funcionou".

### Não faça

- Não confiar no “sync ok” como prova de “install ok”.
- Não usar `source: "./subpasta"` como única estratégia para marketplace por URL raw.
- Não usar slug igual para marketplace e plugin.
- Não declarar componentes ao mesmo tempo no marketplace entry e no `plugin.json` (a menos que saiba exatamente o contrato de precedência).
- Não distribuir dois `plugin.json` com o mesmo `name` em caminhos diferentes dentro do mesmo pacote.
- Não validar apenas no CLI headless e concluir sobre UX do app sem testar no Cowork Desktop.
- Não usar como evidência final uma conversa que começou antes da instalação do plugin.

## 5) Sequência de validação mínima (antes de anunciar pronto)

1. Validar manifests:
   - `claude plugin validate marketplace.json`
   - `claude plugin validate .claude-plugin/marketplace.json`
   - `claude plugin validate plugin.json`
   - `claude plugin validate .claude-plugin/plugin.json`
2. Ambiente limpo (idealmente com HOME temporário para evitar cache antigo).
3. Matriz de instalação:
   - add marketplace por URL raw
   - sincronizar
   - instalar
4. Verificar `claude plugin list --json` sem `errors`.
5. Abrir conversa nova no Cowork Desktop (ou forçar reinit) antes do teste de slash.
6. Validar no Cowork Desktop (não só CLI), incluindo os comandos de runtime e qualquer slash command novo da release.

## 6) Logs e observabilidade (onde olhar quando der erro genérico)

### Arquivo principal de erro do app

- `~/Library/Logs/Claude/main.log`

Padrões úteis:
- `Failed to install plugin`
- `Source path does not exist`
- `ENAMETOOLONG`
- `conflicting manifests`

### Quando o problema é só daquela sessão

Olhe o `audit.jsonl` da sessão:
- em `subtype: "init"`, confira `slash_commands`, `skills` e `plugins`.
- se não houver entradas `prumo:*` e não houver plugin `prumo` em `plugins`, a sessão nasceu sem esse plugin.
- se outra sessão mais nova mostrar `prumo:*`, o problema é de bootstrap de sessão, não de manifesto.

### Quando o toast aparece, mas o plugin está carregado

Se o `init` da sessão já tiver `prumo:*` em `slash_commands` e `prumo` em `plugins`, mas o app mostrar "comando desconhecido":
- verifique se o comando realmente foi enviado ao backend (no `audit.jsonl` deve aparecer mensagem do usuário com `/prumo:...` ou `tool_use` da skill).
- se não houver esse evento, o bloqueio aconteceu no parser de input do cliente (caractere extra, formatação inválida, ou rejeição local antes de enviar).
- teste de forma controlada: digitar exatamente `/briefing`, sem ponto/espaço extra, e preferir seleção pelo autocomplete.

### Evidência típica de falha por source relativo

- `Failed to install plugin "...": Source path does not exist: .../marketplaces/<name>/<relative-source>`

## 7) Armadilha de cache do raw (importante)

Mesmo após merge, a URL `raw` pode servir conteúdo antigo por alguns minutos dependendo de cache.

Para diagnóstico imediato:
- teste com URL fixada em commit:
  - `https://raw.githubusercontent.com/ORG/REPO/<commit>/marketplace.json`

Depois de estabilizar:
- volte para `.../main/marketplace.json`.

## 8) Checklist de release para outro projeto

1. Ajustar manifests com padrão seguro.
2. Rodar validações `claude plugin validate`.
3. Rodar instalação em ambiente limpo.
4. Validar no app desktop:
   - add marketplace por URL
   - sync
   - install
   - comandos do plugin
5. Só então comunicar “instalação via marketplace está ok”.

## 9) Contingência operacional (se produção ainda falhar)

1. Fixar URL por commit do `marketplace.json` para eliminar cache velho.
2. Pedir retry no app após remover marketplace antigo e adicionar de novo.
3. Capturar erro exato + trecho do `main.log`.
4. Se necessário, usar o caminho canônico por CLI:
   - `claude plugin marketplace add <url-do-marketplace>`
   - `claude plugin install prumo@prumo-marketplace`
5. Se necessário, manter `.zip` como fallback temporário com prazo de remoção.

## 10) Nota prática sobre testes de comando

`claude -p "/plugin:comando"` pode não reproduzir fielmente o runtime do Cowork Desktop para skills slash do app.  
Use o app para teste final de comandos.

## 11) Resultado final esperado (sinal de saúde)

- Marketplace aparece corretamente.
- Instalação conclui sem “Falha ao instalar plugin”.
- `claude plugin list --json` mostra plugin sem campo `errors`.
- Comandos principais respondem no runtime do Cowork Desktop.

## 12) Protocolo de 60 segundos (anti "comando desconhecido")

Use este roteiro toda vez que instalar/atualizar plugin e o slash command falhar.

1. Instale/atualize o plugin no Cowork.
2. Feche a conversa onde você testou antes (não precisa apagar nada).
3. Abra uma conversa nova.
4. Digite `/` e confira se aparece `briefing` no autocomplete.
5. Se a release adicionou comando novo, confira também se ele aparece no autocomplete (ex.: `higiene`).
6. Se aparecer, execute o comando afetado e siga a vida.
7. Se não aparecer:
   - faça restart do app Cowork;
   - abra nova conversa e teste de novo.
8. Se ainda não aparecer, só então trate como incidente técnico e colete logs.

Regra de ouro:
- Se o teste foi feito numa sessão aberta antes da instalação, esse teste não vale. Refaça em sessão nova.

Armadilha de UI (importante):
- o submenu `Plugins` do `/` não é prova de disponibilidade de slash commands do plugin.
- valide no submenu `Comandos` (ou digitando `/` e procurando o nome curto do comando).
