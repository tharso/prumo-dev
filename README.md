# Prumo

**Sistema de organização de vida pessoal com IA.**

Prumo é um plugin de IA que transforma o Claude, Codex ou Gemini em interface única para capturar, processar, lembrar e cobrar tudo que acontece na sua vida. Trabalho, filhos, contas, saúde, ideias — tudo entra pelo mesmo lugar.

Seus dados ficam em arquivos Markdown no seu computador. Sem cloud, sem conta, sem lock-in.

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

### Opção 1: Marketplace por URL (recomendada)

Na sua plataforma, use a URL do marketplace:

```
https://raw.githubusercontent.com/tharso/prumo/main/marketplace.json
```

### Opção 2: Repositório Git

```
https://github.com/tharso/prumo.git
```

### Opção 3: Upload local (.zip)

Baixe o repositório e instale manualmente como pacote local.

### Após instalar

1. Abra uma nova conversa na sua plataforma (Claude Desktop, Codex ou Gemini)
2. Selecione uma pasta no seu computador para o Prumo organizar seus arquivos
3. Digite `/prumo:setup`

O setup é um wizard conversacional — uma pergunta por vez, tudo reversível. Leva uns 15 minutos.

Se preferir ir direto ao ponto: `/prumo:start` — você despeja tudo que tem na cabeça e o sistema organiza na hora.

## Comandos

| Comando | O que faz |
|---------|-----------|
| `/prumo:setup` | Setup completo (wizard de 10 etapas) |
| `/prumo:start` | Onboarding rápido — despeje e o sistema organiza |
| `/prumo:briefing` | Briefing diário (pauta, inbox, calendário, emails) |
| `/prumo:handover` | Handover entre agentes (abrir, responder, listar, fechar) |
| `/prumo:sanitize` | Compacta estado operacional sem perder histórico |

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

Se aparecer "comando desconhecido" após instalar/atualizar, consulte `COWORK-MARKETPLACE-PLAYBOOK.md` (seção "Protocolo de 60 segundos").

## Versão

Versão atual: `4.2.3`

## Licença

MIT

---

[prumo.me](https://prumo.me)
