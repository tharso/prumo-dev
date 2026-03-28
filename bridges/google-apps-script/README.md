# Bridge arquivada: Google Apps Script snapshots

Este material existe como arquivo de referência. Não é direção do MVP atual nem prioridade do produto neste momento.

Pelo [ADR-001-GOOGLE-INTEGRATION.md](/Users/tharsovieira/Documents/DailyLife/Prumo/ADR-001-GOOGLE-INTEGRATION.md), a direção estrutural do runtime é Google APIs diretas. Apps Script + Drive continua valendo como:

1. ponte pragmática;
2. fallback host-neutral;
3. trilha histórica caso o projeto precise reabrir esse caminho no futuro.

Não vale tratá-lo como:

1. espinha dorsal definitiva do runtime;
2. desculpa para manter briefing acoplado ao Cowork;
3. camada “provisória” que mora em pasta ignorada e ninguém mais consegue auditar.

## Status de produto

Para o MVP atual, esta ponte fica fora do horizonte ativo.

Em português direto:

1. uma conta Google bem integrada já compra valor suficiente para o piloto;
2. mas não entra agora como requisito do MVP, porque seria um ótimo jeito de trocar foco por cobertura ornamental.

## Artefatos rastreáveis

1. [apps-script-setup.md](/Users/tharsovieira/Documents/DailyLife/Prumo/bridges/google-apps-script/apps-script-setup.md)
2. [email-snapshot-personal-template.gs](/Users/tharsovieira/Documents/DailyLife/Prumo/bridges/google-apps-script/email-snapshot-personal-template.gs)
3. [email-snapshot-work-template.gs](/Users/tharsovieira/Documents/DailyLife/Prumo/bridges/google-apps-script/email-snapshot-work-template.gs)

## Regra de bolso

Se a pergunta for “isso substitui a integração Google do runtime?”, a resposta é não.

Se a pergunta for “isso orienta a arquitetura atual?”, a resposta é não.
