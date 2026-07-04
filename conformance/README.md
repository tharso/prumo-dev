# conformance/ — suíte de conformidade comportamental

O Prumo prova, com testes, o **texto** das regras e o comportamento do runtime.
Esta pasta prova o elo que faltava: os contratos críticos como **comportamento
de um agente real** operando as skills. Contexto e defeito na issue #157 (épico
#161).

## Mapa

- **`SPEC.md`** — a especificação: contratos, classificação de oráculos, como
  rodar, retenção, custo, como adicionar cenário, e o follow-up (A1/A2). Comece
  por aqui.
- **`harness/`** — `oracles.py` (funções puras que decidem o contrato),
  `scenarios.py` (o registro do que se testa), `hosts.py` (replay determinístico
  + adapter real `claude -p`), `run.py` (runner/CLI).
- **`fixtures/scenarios/`** — workspaces iniciais versionados dos cenários.
- **`fixtures/injection/`** — os 5 vetores de injeção da #156; viram cenários de
  transcript em A1 (C12).

## Rodar agora (determinístico, sem LLM)

```
PYTHONPATH=runtime python -m unittest runtime.tests.test_conformance
```

Isso roda em CI a cada PR. A execução com o agente real é o passo de cadência do
dono — ver `SPEC.md → Rodando → De verdade`.
