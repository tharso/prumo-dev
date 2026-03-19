# Prumo

**Sistema de organização de vida pessoal com IA.**

Versão atual: **4.7.2**

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

### Opção 1: Marketplace Git no Cowork (recomendada)

No Cowork, o caminho mais confiável hoje é adicionar o marketplace pelo repositório Git:

```text
https://github.com/tharso/prumo.git
```

Isso reduz o risco de catálogo congelado e evita boa parte da pantomima que a UI consegue encenar quando o checkout local envelhece parado.

### Opção 2: CLI canônico (backend do Claude)

Se você usa o backend do `claude` no terminal, este é o caminho canônico.
Para Cowork, ele ajuda, mas não substitui o store local do app quando a UI decide envelhecer sentada.

```bash
claude plugin marketplace add https://github.com/tharso/prumo.git
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

### Opção 3: Doctor e update do Cowork

Se o Cowork mostrar versão velha, deixar `Atualizar` morto ou jurar que está sincronizado enquanto lê jornal de ontem:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_cowork_doctor.sh)
```

Se o diagnóstico apontar checkout congelado do marketplace:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/tharso/prumo/main/scripts/prumo_cowork_update.sh)
```

Depois:
1. feche totalmente o Cowork;
2. abra o app de novo;
3. se ainda precisar, remova só o plugin `Prumo` e reinstale a partir do marketplace.

### Opção 4: Marketplace por URL raw na UI

Use a URL abaixo só como compatibilidade ou debug:

```text
https://raw.githubusercontent.com/tharso/prumo/main/marketplace.json
```

Observação importante:
o fluxo por `raw` pode parecer atualizado e continuar velho por baixo. Se o app disser "comando desconhecido", travar em versão antiga ou apagar o botão de update, trate isso como drift de catálogo. Não como azar metafísico.

### Opção 5: Upload local (.zip)

Baixe o repositório e instale manualmente como pacote local. Funciona, mas envelhece mal e cobra pedágio depois.

### Após instalar

1. Abra uma nova conversa na sua plataforma (Claude Desktop, Codex ou Gemini)
2. Selecione uma pasta no seu computador para o Prumo organizar seus arquivos
3. Digite `/setup`

O setup é um wizard conversacional — uma pergunta por vez, tudo reversível. Leva uns 15 minutos.

Se preferir ir direto ao ponto: `/start` — você despeja tudo que tem na cabeça e o sistema organiza na hora.

## Comandos

No Cowork, os slash commands do Prumo aparecem sem prefixo do plugin. Use `/setup`, `/briefing`, `/doctor`, `/handover`, `/sanitize`, `/higiene` e `/start`.

| Comando | O que faz |
|---------|-----------|
| `/setup` | Setup completo (wizard de 10 etapas) |
| `/start` | Onboarding rápido — despeje e o sistema organiza |
| `/briefing` | Briefing diário (pauta, inbox, calendário, emails) |
| `/doctor` | Diagnóstico do runtime do Prumo no Cowork (store, marketplace, drift de versão) |
| `/handover` | Handover entre agentes (abrir, responder, listar, fechar) |
| `/sanitize` | Sanitiza estado operacional e arquiva histórico frio com rastreabilidade |
| `/higiene` | Diagnostica e propõe limpeza assistida do `CLAUDE.md`, separando limpeza segura, confirmação factual, governança e avisando sobre core defasado |

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

Se aparecer "comando desconhecido" após instalar/atualizar, o suspeito principal é sessão velha, app sem restart, comando digitado com prefixo errado ou marketplace congelado num checkout velho.
Feche a conversa, abra uma nova, teste o autocomplete de `/setup`, `/briefing`, `/doctor`, `/handover`, `/sanitize`, `/higiene` e, se preciso, reinicie o Cowork antes de decretar bug no plugin.

Se o painel do app disser que atualizou, mas o plugin continuar em versão velha ou sumirem comandos novos, rode o `doctor` do Cowork. O painel às vezes sorri e não faz o serviço. Concierge de hotel ruim.

## Versão

Versão atual: `4.7.2`

## Licença

MIT

---

[prumo.me](https://prumo.me)
