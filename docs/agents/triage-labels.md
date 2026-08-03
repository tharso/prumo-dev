# Labels de triagem

As skills falam em cinco papéis canônicos de triagem. Esta tabela mapeia cada papel para o label que este repo realmente usa.

O `prumo-dev` já tinha um vocabulário de status com prefixo `status/` antes das skills chegarem. Os papéis foram mapeados para ele em vez de criar um segundo vocabulário paralelo — três dos cinco já existiam.

| Papel nas skills  | Label neste repo      | Significado                                       |
| ----------------- | --------------------- | ------------------------------------------------- |
| `needs-triage`    | `status/triage`       | Aguardando refinamento                            |
| `needs-info`      | `status/needs-info`   | Esperando informação de quem reportou             |
| `ready-for-agent` | `status/ready`        | Especificada, pronta para execução por agente     |
| `ready-for-human` | `status/ready-human`  | Exige implementação humana                        |
| `wontfix`         | `wontfix`             | Não será tratada                                  |

Quando uma skill mencionar um papel (ex.: "aplique o label de pronta para agente"), use o label da coluna do meio.

## Cuidado com dois vizinhos

- **`status/needs-review`** ("Issue parece concluída e precisa de revisão humana antes de fechar") **não** é `needs-info`. Ele fica no fim do ciclo, não no começo: a issue está pronta e espera o Tharso fechar. Confundir os dois manda de volta pra fila uma issue que já acabou.
- **`status/blocked`** ("Bloqueada") também não é `needs-info` — bloqueio é dependência externa, não falta de informação de quem reportou.

Os labels `type/*`, `priority/*`, `area/*` e `agent/*` são ortogonais à triagem e convivem com os de cima. Nenhuma skill precisa aplicá-los.
