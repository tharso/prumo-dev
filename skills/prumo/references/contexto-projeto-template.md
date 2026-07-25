# Template do `.prumo-contexto.md` (contexto de projeto, #201)

> Arquivo ÚNICO na **raiz do projeto** (não é pasta `.prumo/` — pasta colidiria
> com a detecção de workspace do runtime). É a narrativa do projeto que o
> Prumo lê quando a intenção pedir ("como está o projeto X?") e cujo
> `updated:` alimenta o frescor do índice (`prumo projetos --sync`).
>
> Quem atualiza: o agente que trabalha NO projeto, ao encerrar uma sessão de
> trabalho relevante (convenção a registrar no CLAUDE.md do projeto). Esquecer
> não quebra nada: o pulso mecânico (git/mtime) continua, e o índice marca a
> narrativa como possivelmente defasada — o sistema denuncia, nunca mente.
>
> O `updated:` DEVE ser RFC 3339 com hora e offset (ex.:
> `2026-07-24T18:30:00-03:00`). Só data (`2026-07-24`) funciona, mas empata
> com atividade do mesmo dia e vira frescor `indeterminate`.

---

INÍCIO DO TEMPLATE:

---

---
updated: {{RFC3339_AGORA}}
---

# {{NOME_DO_PROJETO}} — contexto

## O que é

{{Uma ou duas frases: o que este projeto é e pra quem.}}

## Estado atual

{{O retrato honesto de agora: o que funciona, o que está pela metade, o que está quebrado.}}

## Decisões recentes

- {{decisão + data + por quê, mais recente primeiro}}

## Próximos passos

- {{o que vem a seguir, em ordem}}

## Bloqueios / esperando

- {{o que trava e quem destrava; vazio se nada}}
