# Cowork Runtime Maintenance

> **module_version: 4.16.6**
>
> Fonte canônica para instalação, diagnóstico e atualização do Prumo no Cowork.

## Instalação recomendada no Cowork

Para o Cowork, o caminho canônico do marketplace é o repositório Git:

```text
https://github.com/tharso/prumo.git
```

`raw marketplace.json` continua útil como compatibilidade e debug, mas não é mais o caminho preferencial para usuário final no Cowork.

## O que o produto deve assumir

1. O botão `Atualizar` da UI do Cowork é sinal fraco, não fonte da verdade.
2. O estado real mora no store local do Cowork:
   - `known_marketplaces.json`
   - `installed_plugins.json`
   - checkout em `marketplaces/<marketplace-name>/`
3. Se o checkout do marketplace congelar num commit velho, a UI pode:
   - mostrar versão antiga;
   - deixar `Atualizar` desabilitado;
   - parecer sincronizada sem estar.

## Scripts canônicos

- `prumo_cowork_doctor.sh`
  Diagnostica store local, checkout do marketplace, versão instalada e drift de catálogo.

- `prumo_cowork_update.sh`
  Atualiza os checkouts do marketplace do Prumo usados pelo Cowork e renova o timestamp de sync.

## Política de update

1. Primeiro diagnosticar.
2. Se o checkout do marketplace estiver defasado, atualizar o checkout.
3. Só depois discutir reinstalação do plugin.
4. Não editar `installed_plugins.json` na marra como atalho de produto. Isso é cirurgia no escuro.

## Regra operacional

Se o runtime do Cowork e o catálogo local divergirem, o Prumo deve apontar o drift com nome e sobrenome.
Usuário não deveria precisar discutir com botão cinza para descobrir que o checkout do marketplace está preso no passado.
