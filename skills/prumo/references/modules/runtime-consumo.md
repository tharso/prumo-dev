# Contrato de consumo e invocação do runtime

> **module_version: 1.0.0**
>
> Dono ÚNICO do contrato de consumo E de invocação (#228 C1 e fase 2 —
> morava nas "Regras rápidas" da porta e dos wrappers, pesando na abertura de
> TODA sessão; só é preciso quando um comando do runtime vai rodar).
> **Carregar antes de QUALQUER comando `prumo`** — start, briefing, repair,
> setup, migrate, doctor: as regras 10–13 valem pra toda invocação, e a
> ESCOLHA do formato (JSON ou não, regras 1–3) é parte do contrato, não
> consequência dele. Os wrappers e a porta apontam pra cá.

## As regras

1. Para o painel local estruturado (semente/backcompat), `prumo briefing --workspace . --format json`.
2. Se o host souber trabalhar com JSON, prefira `prumo start --format json`.
3. Se o host conseguir renderizar ações próprias, preferir `prumo start --format json` em vez de reinventar onboarding na unha.
4. Se usar JSON, leia `adapter_hints` e respeite `kind`, `shell_command` e `host_prompt`.
5. Ao consumir JSON estruturado, o host deve ler `adapter_contract_version`, `workspace_resolution` e `adapter_hints` antes de bancar o esperto.
6. Antes de olhar `message`, leia `state_flags`, `degradation`, `next_move` e `selection_contract`. A prosa vem depois.
7. Se `degradation.status` vier `error` ou `partial`, preserve o que ainda presta, mostre o tropeço em uma linha curta e, se houver `action_id` útil, priorize essa recuperação antes de inventar novo ritual.
8. Não fabrique JSON de `prumo start --format json` ou `prumo briefing --workspace . --format json`. Ou retorna a saída real, ou assume que falhou.
9. Se `next_move.id == kickoff`, não abra cardápio de aeroporto. Faça uma segue curta e convide ao despejo inicial.

> As regras 2 e 3 seguem NÃO unificadas de propósito (decisão do dono na
> #179): os predicados diferem em substância — "renderizar ações próprias"
> ⊂ "saber trabalhar com JSON".

10. **Não simule comando.** Não leia arquivo para simular `prumo`, `briefing` ou `start`. Primeiro execute o comando real.
11. **Não escreva estado do runtime à mão.** Não escreva `.prumo/state/` fingindo ser o runtime. No layout flat o caminho é `_state/`; foi o bug da #214.
12. **Sem comando por curiosidade.** Não rode comando extra só porque ficou curioso. Execute o que foi pedido ou o que o runtime sugeriu.
13. **Sem disco riscado.** Se um comando falhar por uso ou argumento inválido, não repita a mesma linha como disco riscado.

> As quatro acima moravam nas "Regras rápidas" da porta e vinham na abertura de TODA sessão (#228, fase 2): são contrato de INVOCAÇÃO — pertencem aqui. **Valem para QUALQUER comando `prumo`** (start, briefing, repair, setup, migrate, doctor...), não só os que consomem JSON: por isso o gatilho deste módulo é qualquer invocação do runtime.
