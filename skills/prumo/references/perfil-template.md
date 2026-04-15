# Template do Prumo/Agente/PERFIL.md (configuração pessoal)

> Este template gera o arquivo `Prumo/Agente/PERFIL.md` — configuração
> pessoal do usuário. Contém áreas de vida, tom, lembretes, integrações
> e informações pessoais.
>
> Equivale ao antigo CLAUDE.md pessoal, mas agora vive dentro de `Prumo/Agente/`
> separado das regras do sistema (.prumo/system/PRUMO-CORE.md) e da
> navegação (Prumo/AGENT.md).
>
> O agente de setup deve preencher os placeholders `{{VARIAVEL}}` e resolver
> as seções condicionais `{{#SE_X}}...{{/SE_X}}`. O resultado NÃO deve conter
> nenhum placeholder — deve ser texto natural e específico para o usuário.
>
> REGRA DE ESCRITA: NÃO copiar literalmente. Usar como guia e escrever
> de forma natural e específica para o usuário.

---

INÍCIO DO TEMPLATE:

---

# Perfil — {{USER_NAME}}

> Configuração pessoal. Nunca atualizado automaticamente.
> Agente: **{{AGENT_NAME}}**

---

## Quem é {{USER_NAME}}

{{USER_NAME}} tem {{PROBLEMA_PRINCIPAL}}. Isso resulta em pendências eternas, SLA ruim de resposta, e coisas importantes que saem do radar.

{{AGENT_NAME}} funciona como interface única para capturar, processar, lembrar e cobrar.

---

## Áreas de vida

{{AREAS_DESCRICAO}}

---

## Configuração

### Horários e rituais

- **Briefing**: {{BRIEFING_TIME}} (dizer "bom dia" ou "briefing")
- **Revisão semanal**: {{REVIEW_DAY}}
- **Fuso**: {{TIMEZONE}}

### Tom

{{TOM_COMUNICACAO}}

{{TOM_REGRA_COBRANCA}}

{{TOM_BRIEFING}}

### Lembretes recorrentes estáveis

{{LEMBRETES_RECORRENTES}}

> Só entram aqui lembretes estáveis e recorrentes.
> Pendência datada vai para `Prumo/PAUTA.md`. Coisa resolvida vai para `Prumo/REGISTRO.md`.

---

{{#SE_INTEGRACOES}}
## Integrações

{{INTEGRACOES_DETALHE}}

{{/SE_INTEGRACOES}}

### Input mobile

{{USER_NAME}} pode capturar notas e tarefas pelo celular:

1. **Pasta Prumo/Inbox4Mobile/**: Enviar arquivos, notas, screenshots, fotos
{{#SE_GMAIL}}
2. **Email com subject "{{AGENT_NAME}}"**: Captura rápida (pode incluir contexto no subject)
3. **Email com subject "INBOX:"**: Formato alternativo

**Rotina de captura:** 1-2x por dia, buscar no Gmail por `subject:{{AGENT_NAME}}` e `subject:INBOX:`
{{/SE_GMAIL}}

---

## Tags

{{TAGS_LIST}}

---

## Informações pessoais

{{USER_INFO}}

---

## Changelog

- **{{DATA_SETUP}}**: Sistema criado via Prumo. {{RESUMO_SETUP}}.

---

*Criado com Prumo — Última atualização: {{DATA_SETUP}}*
