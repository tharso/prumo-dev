# Contrato de consumo do JSON do runtime

> **module_version: 1.0.0**
>
> Dono ÚNICO do contrato de consumo (#228 C1 — morava nas "Regras rápidas"
> da porta e dos wrappers, pesando na abertura de TODA sessão; só é preciso
> quando um comando do runtime vai rodar). Carregar **antes de invocar
> `prumo start`/`prumo briefing` — a ESCOLHA do formato (JSON ou não, regras
> 1–3) é parte do contrato**, não consequência dele. Os wrappers e a porta
> apontam pra cá.

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
