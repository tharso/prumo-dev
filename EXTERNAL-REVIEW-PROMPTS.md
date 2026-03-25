# External Review Prompts

## Prompt para Claude

Leia primeiro:

1. [EXTERNAL-REVIEW-BRIEF.md](/Users/tharsovieira/Documents/DailyLife/Prumo/EXTERNAL-REVIEW-BRIEF.md)
2. [README.md](/Users/tharsovieira/Documents/DailyLife/Prumo/README.md)
3. [CHANGELOG.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CHANGELOG.md)
4. [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md)
5. [PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md](/Users/tharsovieira/Documents/DailyLife/Prumo/PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md)
6. [runtime/prumo_runtime/daily_operator.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/daily_operator.py)
7. [runtime/prumo_runtime/commands/start.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/commands/start.py)
8. [runtime/prumo_runtime/commands/briefing.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/commands/briefing.py)

Quero uma revisao critica do estado atual do Prumo.

Nao me trate como fundador que precisa de colo.
Me trate como alguem que precisa evitar erro caro de produto e arquitetura.

Quero que voce responda em 4 blocos:

1. `Veredito`
2. `O que esta forte`
3. `O que esta torto`
4. `Proximo corte`

Se encontrar premissas frageis, diga na lata.
Se achar que estamos sofisticando cedo demais, diga.
Se achar que a estrategia de host esta errada, diga.

Quero enfase especial em:

1. quao perto estamos de recuperar a fluidez do legado sem voltar ao acoplamento antigo
2. se `next_move` + `selection_contract` + `actions[]` realmente bastam para disciplinar hosts
3. se o piloto via `Antigravity` ja parece produto ou ainda parece demo de infraestrutura
4. quais sao os 3 riscos mais subestimados agora

No fim, me diga tambem:
"Se eu tivesse que apostar dinheiro neste piloto hoje, eu estaria preocupado com X."

## Prompt para Gemini

Leia primeiro:

1. [EXTERNAL-REVIEW-BRIEF.md](/Users/tharsovieira/Documents/DailyLife/Prumo/EXTERNAL-REVIEW-BRIEF.md)
2. [README.md](/Users/tharsovieira/Documents/DailyLife/Prumo/README.md)
3. [CHANGELOG.md](/Users/tharsovieira/Documents/DailyLife/Prumo/CHANGELOG.md)
4. [INVOCATION-UX-CONTRACT.md](/Users/tharsovieira/Documents/DailyLife/Prumo/INVOCATION-UX-CONTRACT.md)
5. [HOST-ADAPTER-IMPLEMENTATION-PLAN.md](/Users/tharsovieira/Documents/DailyLife/Prumo/HOST-ADAPTER-IMPLEMENTATION-PLAN.md)
6. [PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md](/Users/tharsovieira/Documents/DailyLife/Prumo/PRUMO-PLUGIN-VS-RUNTIME-COMPARISON.md)
7. [runtime/prumo_runtime/daily_operator.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/daily_operator.py)
8. [runtime/prumo_runtime/commands/start.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/commands/start.py)
9. [runtime/prumo_runtime/commands/briefing.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/commands/briefing.py)

Quero uma revisao critica do Prumo como produto e como arquitetura de runtime local-first.

Nao quero resumo neutro. Quero julgamento.

Responda em 4 blocos:

1. `Veredito`
2. `O que esta forte`
3. `O que esta torto`
4. `Proximo corte`

Foque em responder:

1. Estamos construindo um produto diario de verdade ou ainda estamos presos num "briefing engine" mais sofisticado?
2. O desenho atual parece escalavel para multiplos hosts ou ainda depende demais de comportamento benevolente do host?
3. O que ainda separa o Prumo atual da fluidez percebida no plugin antigo?
4. O que esta com cara de complexidade precoce?
5. Qual seria o escopo minimo para um piloto comercial realmente defensavel nas proximas semanas?

Se voce achar que estamos errando a prioridade, diga sem perfume.
