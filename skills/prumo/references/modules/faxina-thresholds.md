# Thresholds da Faxina

Limites ajustáveis em `Prumo/Custom/rules/` (ver "Customização").

## Registro

| Parâmetro | Valor padrão | O que significa |
|-----------|-------------|----------------|
| max_items | 50 | Acima disso, arquivar os mais velhos |
| archive_age_days | 30 | Itens com mais de 30 dias vão pro arquivo |

## Inbox

| Parâmetro | Valor padrão | O que significa |
|-----------|-------------|----------------|
| processed_expiry_days | 14 | Entradas processadas há mais de 14 dias são limpas |
| declared_inbox_stale_days | 14 | Caixa declarada no mapa autoral com item mais velho: higiene sinaliza (#245) |

## Cache e backups

| Parâmetro | Valor padrão | O que significa |
|-----------|-------------|----------------|
| backup_expiry_days | 90 | Backups mais velhos que 90 dias são removidos |
| cache_expiry_days | 30 | Cache além de 30 dias é limpo |

## Índices

| Parâmetro | Valor padrão | O que significa |
|-----------|-------------|----------------|
| referencias_subcategorize_at | 30 | Acima de 30 itens, agrupar por tema |

## Diário

| Parâmetro | Valor padrão | O que significa |
|-----------|-------------|----------------|
| diario_expiry_days | 90 | Arquivo do `Diario/` com data no nome além disso é rotacionado |

## Customização

Pra ajustar, criar `Prumo/Custom/rules/faxina-thresholds.md` com **os MESMOS
nomes das tabelas acima** (apelido novo não é override, é dialeto):

```markdown
# Thresholds customizados da faxina

- max_items: 100
- archive_age_days: 60
- processed_expiry_days: 7
```

A faxina checa `Prumo/Custom/rules/faxina-thresholds.md` primeiro.
Se existir, usa os valores de lá. Se não, usa os padrões acima.

**Override × semente do runtime:** a semente pré-calcula sinais com os
DEFAULTS e **declara o número usado** (`local_panorama.faxina.stale_days_threshold`).
Com override cujo valor difira do declarado, a checagem daquela família **não
pode usar o pré-calculado** — recalcular direto da fonte (ex.: `_processed.json`).
