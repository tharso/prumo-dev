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
| curated_shrink_alert_pct | 40 | Arquivo curado que encolheu mais que isso (%, teto 100) desde a última cópia vira alerta (#262) |

## Índices

| Parâmetro | Valor padrão | O que significa |
|-----------|-------------|----------------|
| referencias_subcategorize_at | 30 | Acima de 30 itens, agrupar por tema |
| referencias_id_gap_alert_pct | 50 | Lacunas de ID (%, teto 100) além disso: índice suspeito, faxina bloqueia (#261) |
| referencias_bulk_reindex_at | 5 | Fichas fora do índice a partir deste número: não são "novas", faxina bloqueia (#261) |

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

**Override × semente do runtime (mecânica v1, #258):** o **runtime aplica** o
override e a semente transporta os thresholds **efetivos** em
`local_panorama.faxina.thresholds` (com `schema: prumo_faxina_thresholds.v1`,
`thresholds_source` e `override_keys`); o pré-cálculo usa esses valores. Não há
mais divergência entre o número declarado e o número usado — a regra antiga de
"recalcular direto da fonte quando diferirem" **foi revogada por construção**.
Este doc entra na rota quando não há semente, o schema é outro **ou o override divergiu da semente** (#258).
