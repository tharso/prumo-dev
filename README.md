# Prumo

**Sistema de organização de vida pessoal com IA.**

Versão atual: **4.6.1**

Prumo é um plugin de IA que transforma o Claude, Codex ou Gemini em interface única para capturar, processar, lembrar e cobrar tudo que acontece na sua vida. Trabalho, filhos, contas, saúde, ideias — tudo entra pelo mesmo lugar.

Para email e agenda multi-conta, o fluxo preferencial agora usa snapshots privados no Google Drive gerados por Google Apps Script e gravados como Google Docs com JSON texto. O motor do Prumo também saiu do formato armário de acumulador: o core agora é índice + guardrails, com procedimento detalhado em módulos canônicos. E a sanitização deixou de ser só “compactar handover”: o sistema agora já consegue arquivar frio seguro com índice global, sem brincar de sumiço.

Seus dados ficam em arquivos Markdown no seu computador. Sem cloud, sem conta, sem lock-in.
E, a partir de agora, com um pouco mais de governo: o Prumo começou a explicitar o que pertence a `CLAUDE.md`, `PAUTA.md`, `REGISTRO.md` e histórico, em vez de fingir que tudo cabe no mesmo armário.

## O problema

Você tem 47 coisas na cabeça: o email que precisa responder, a reunião que precisa preparar, o exame que depende do pedido médico que você ainda não pediu. Aí você baixa um app de produtividade — e duas semanas depois ele virou mais uma pendência na lista de pendências.

Prumo funciona diferente: você despeja o caos, ele organiza. Sem dashboard pra manter, sem card pra arrastar, sem disciplina sobre-humana.

## Como funciona

1. **Captura** — Despeje tudo que está na sua cabeça. Texto, áudio, foto, email. Do computador ou do celular.
2. **Processamento** — Prumo separa, categoriza e extrai próximas ações. "Renovar passaporte, o Fulano manda o contrato amanhã e tive uma ideia de app" vira três itens em três contextos diferentes.
3. **Briefing diário** — Todo dia, Prumo traz o que importa: pendências, prazos, emails sem resposta, compromissos. Você só reage.
4. **Revisão semanal** — Varredura periódica pra nada cair do radar.

## Instalação

Prumo funciona com **Claude Desktop (Cowork)**, **Codex CLI** e **Gemini CLI**.

### Opção 1: CLI canônico (recomendada)

Se você usa Claude Desktop/Cowork, este é o caminho mais confiável hoje.
Sim, eu preferia poder dizer "clica no botão bonito". O produto ainda não ganhou esse luxo.

```bash
claude plugin marketplace add https://raw.githubusercontent.com/tharso/prumo/main/marketplace.json
claude plugin install prumo@prumo-marketplace
```

Para atualizar depois:

```bash
claude plugin marketplace update prumo-marketplace
claude plugin update prumo@prumo-marketplace
```

Se quiser um instalador sóbrio, sem copiar comando em duas etapas:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_plugin_install.sh)
```

### Opção 2: Marketplace por URL na UI

Use a URL abaixo no painel do app:

```
https://raw.githubusercontent.com/tharso/prumo/main/marketplace.json
```

Observação importante:
o fluxo por UI pode parecer atualizado e continuar velho por baixo. Se o app disser "comando desconhecido" ou mostrar versão antiga, use o caminho por CLI acima e poupe seu tempo.

### Opção 3: Repositório Git

```
https://github.com/tharso/prumo.git
```

### Opção 4: Upload local (.zip)

Baixe o repositório e instale manualmente como pacote local.

### Após instalar

1. Abra uma nova conversa na sua plataforma (Claude Desktop, Codex ou Gemini)
2. Selecione uma pasta no seu computador para o Prumo organizar seus arquivos
3. Digite `/setup`

O setup é um wizard conversacional — uma pergunta por vez, tudo reversível. Leva uns 15 minutos.

Se preferir ir direto ao ponto: `/start` — você despeja tudo que tem na cabeça e o sistema organiza na hora.

## Comandos

No Cowork, os slash commands do Prumo aparecem sem prefixo do plugin. Use `/setup`, `/briefing`, `/handover`, `/sanitize`, `/higiene` e `/start`.

| Comando | O que faz |
|---------|-----------|
| `/setup` | Setup completo (wizard de 10 etapas) |
| `/start` | Onboarding rápido — despeje e o sistema organiza |
| `/briefing` | Briefing diário (pauta, inbox, calendário, emails) |
| `/handover` | Handover entre agentes (abrir, responder, listar, fechar) |
| `/sanitize` | Sanitiza estado operacional e arquiva histórico frio com rastreabilidade |
| `/higiene` | Diagnostica e propõe limpeza assistida do `CLAUDE.md`, incluindo drift de conteúdo entre arquivos |

## Princípios

- **Tudo local.** Arquivos Markdown em pastas do seu computador. Abra com qualquer editor.
- **Sem lock-in.** Deletou o plugin? Seus arquivos continuam lá — só que melhor organizados.
- **Uma entrada.** Sua vida não tem departamentos. Prumo também não.
- **Proativo.** Prumo não espera você checar. Traz o que importa na hora certa.

## Estrutura do repositório

```
├── plugin.json              # Manifest do plugin
├── marketplace.json         # Manifest do marketplace
├── commands/                # Slash commands (/setup, /briefing, etc.)
├── cowork-plugin/           # Pacote de runtime (skills, scripts, referências)
├── CHANGELOG.md             # Histórico de mudanças
└── VERSION                  # Versão atual
```

## Compatibilidade

- Claude Desktop (Cowork)
- Codex CLI
- Gemini CLI

## Diagnóstico rápido

Se aparecer "comando desconhecido" após instalar/atualizar, o suspeito principal é sessão velha, app sem restart ou comando digitado com prefixo errado.
Feche a conversa, abra uma nova, teste o autocomplete de `/setup`, `/briefing`, `/handover`, `/sanitize`, `/higiene` e, se preciso, reinicie o Cowork antes de decretar bug no plugin.

Se o painel do app disser que atualizou, mas o plugin continuar em versão velha ou sumirem comandos novos, use o caminho canônico por CLI. O painel às vezes sorri e não faz o serviço. Concierge de hotel ruim.

## Versão

Versão atual: `4.6.1`

## Licença

MIT

---

[prumo.me](https://prumo.me)
