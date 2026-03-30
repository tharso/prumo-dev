# Layout do Workspace e politica de adocao

Status: proposta de implementacao do proximo slice

Data: 2026-03-30

Relacionado:

1. [README.md](/Users/tharsovieira/Documents/DailyLife/Prumo/README.md)
2. [PRUMO-CAPABILITY-BACKEND-ARCHITECTURE.md](/Users/tharsovieira/Documents/DailyLife/Prumo/PRUMO-CAPABILITY-BACKEND-ARCHITECTURE.md)
3. [REPO-WORKSPACE-JURISDICTION.md](/Users/tharsovieira/Documents/DailyLife/Prumo/REPO-WORKSPACE-JURISDICTION.md)
4. [runtime/prumo_runtime/commands/setup.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/commands/setup.py)
5. [runtime/prumo_runtime/workspace.py](/Users/tharsovieira/Documents/DailyLife/Prumo/runtime/prumo_runtime/workspace.py)

## 1. O problema

Hoje o runtime faz tres coisas erradas ao mesmo tempo:

1. despeja memoria viva do usuario na raiz do workspace;
2. mistura infraestrutura do sistema com arquivos autorais;
3. trata `setup bem-sucedido` como se isso significasse `primeira experiencia boa`.

Resultado: a raiz fica com cara de bancada de oficina, o usuario fica sem saber o que pode apagar e o primeiro briefing num workspace vazio parece inauguracao de apartamento sem moveis.

## 2. O principio que passa a valer

O workspace precisa ter tres camadas internas, com jurisdição explicita:

1. **raiz minima** para wrappers e descoberta por host;
2. **`Prumo/`** para memoria viva e arquivos autorais do usuario;
3. **`/.prumo/`** para infraestrutura atualizavel do sistema.

Se tudo morar na raiz, o usuario sente invasao. Se tudo for escondido, os hosts tropeçam. A solucao decente e separar interfone, sala e casa de maquinas.

## 3. Topologia alvo

```text
workspace/
├── AGENT.md
├── AGENTS.md
├── CLAUDE.md
├── Prumo/
│   ├── AGENT.md
│   ├── PAUTA.md
│   ├── INBOX.md
│   ├── REGISTRO.md
│   ├── IDEIAS.md
│   ├── Agente/
│   ├── Referencias/
│   ├── Inbox4Mobile/
│   └── Custom/
│       ├── skills/
│       ├── workflows/
│       ├── rules/
│       └── scripts/
└── .prumo/
    ├── state/
    ├── system/
    │   ├── skills/
    │   ├── workflows/
    │   ├── prompts/
    │   └── scripts/
    ├── cache/
    ├── manifests/
    └── logs/
```

Observacao importante:

1. essa e a **topologia alvo**
2. o runtime atual ainda cria um layout flat de transicao
3. esse documento existe justamente para encerrar essa transicao sem improviso

## 4. O que mora em cada camada

### 4.1. Raiz minima

Na raiz devem ficar apenas os wrappers de descoberta:

1. `AGENT.md`
2. `AGENTS.md`
3. `CLAUDE.md`

Esses arquivos nao devem carregar o apartamento inteiro nas costas. Devem ser wrappers curtos e regeneraveis.

Funcao deles:

1. serem encontrados por hosts que so olham a raiz;
2. apontarem para `/Prumo/AGENT.md` como canon de trabalho;
3. declararem a porta curta de invocacao do Prumo;
4. deixarem claro que estado tecnico do sistema fica em `/.prumo/` e memoria viva em `/Prumo/`.

Em portugues simples: a raiz vira campainha, nao almoxarifado.

### 4.2. `Prumo/`

`Prumo/` passa a ser a area de memoria viva do usuario.

Aqui ficam:

1. `AGENT.md` canonico do workspace
2. `PAUTA.md`
3. `INBOX.md`
4. `REGISTRO.md`
5. `IDEIAS.md`
6. `Agente/`
7. `Referencias/`
8. `Inbox4Mobile/`
9. `Custom/`

Regra:

1. isso e legivel pelo usuario;
2. isso nao e terreno livre para update de sistema;
3. isso e parte da casa habitada, nao da oficina do produto.

### 4.3. `/.prumo/`

`/.prumo/` passa a ser a camada de sistema local.

Aqui ficam:

1. `state/`
2. `cache/`
3. `logs/`
4. `manifests/`
5. `system/skills/`
6. `system/workflows/`
7. `system/prompts/`
8. `system/scripts/`

Regra:

1. tudo aqui e atualizavel;
2. nada aqui deve ser tratado como memoria autoral do usuario;
3. o sistema pode regenerar isso sem pedir desculpa, desde que preserve configuracoes e migracoes previstas.

## 5. A area cinzenta: skills e workflows

Skills e workflows nao cabem em duas caixas simples. Parte deles e motor. Parte deles pode virar personalizacao do usuario.

A regra correta nao e escolher um lado. E trabalhar com overlay.

### 5.1. Base do sistema

Fica em:

1. `/.prumo/system/skills/`
2. `/.prumo/system/workflows/`

Essa base pode ser atualizada pelo produto.

### 5.2. Override do usuario

Fica em:

1. `/Prumo/Custom/skills/`
2. `/Prumo/Custom/workflows/`
3. `/Prumo/Custom/rules/`
4. `/Prumo/Custom/scripts/`

Essa camada nao pode ser sobrescrita por update.

### 5.3. Regra de precedencia

Sempre:

1. `custom > system`
2. se nao houver override, o sistema usa a base
3. se a base mudar muito e o override ficar suspeito, o Prumo avisa, mas nao pisa em cima

Nao tratar personalizacao como edicao direta do sistema e a diferenca entre update seguro e reforma em apartamento alugado.

## 6. Politica de update

Update do Prumo deve obedecer estas cercas:

1. pode atualizar `/.prumo/`
2. nao pode sobrescrever `/Prumo/Custom/`
3. nao pode mexer em `PAUTA.md`, `INBOX.md`, `REGISTRO.md`, `IDEIAS.md` e referencias autorais como se fossem asset regeneravel
4. wrappers da raiz podem ser regenerados, mas com politica de adocao clara

## 7. Politica de adocao para arquivos ja existentes na raiz

O caso espinhoso e este:

1. o usuario ja tem `AGENT.md`
2. ou ja tem `AGENTS.md`
3. ou ja tem `CLAUDE.md`

O instalador nao pode agir como turista que senta na cadeira errada e chama a casa de coworking.

### 7.1. Modos de adocao

O `setup` precisa oferecer, de forma explicita, tres modos:

1. **adotar e mesclar** (recomendado)
2. **fazer backup e substituir**
3. **nao tocar na raiz**

### 7.2. Adotar e mesclar

Modo padrao.

O Prumo:

1. preserva o arquivo existente;
2. injeta um bloco curto e delimitado de ponte para `/Prumo/AGENT.md`;
3. evita transformar o arquivo do usuario em panfleto do produto.

### 7.3. Backup e substituir

Para quem quer deixar o Prumo mandar na raiz.

O Prumo:

1. cria backup legivel;
2. escreve wrappers novos e curtos;
3. registra a operacao no `REGISTRO.md` ou em log tecnico apropriado.

### 7.4. Nao tocar na raiz

Modo paranoico e valido.

O Prumo:

1. respeita a decisao;
2. segue funcionando por invocacao explicita;
3. assume que a descoberta automatica por host pode piorar.

## 8. Setup: novo vs adocao

O `setup` atual e bruto demais. Ele pede nome, cria a pasta e despeja arquivos. Isso e carpintaria, nao onboarding.

O fluxo precisa ser redesenhado em steps curtos.

### 8.1. Etapas alvo

1. como a pessoa prefere ser chamada
2. se quer testar com seguranca ou adotar uma pasta existente
3. qual pasta vai virar workspace
4. se quer que o Prumo toque na raiz ou trabalhe com wrappers minimos
5. qual host ela quer usar primeiro
6. como deve ser a primeira sessao

Cada step:

1. uma frase curta
2. opcoes visiveis
3. zero sermão

### 8.2. Dois modos de entrada

#### `Criar workspace novo`

Para quem quer experimentar sem abrir a casa toda.

Aqui o onboarding deve:

1. criar a estrutura
2. explicar o minimo
3. evitar briefing classico vazio
4. abrir uma sessao exploratoria e sedutora de primeiro valor

#### `Adotar pasta existente`

Para quem quer colocar o Prumo num lugar onde ja ha vida.

Aqui o onboarding deve:

1. mostrar o que sera criado
2. perguntar como tratar wrappers existentes
3. deixar claro o que e sistema e o que e usuario
4. so depois seguir

## 9. Primeira sessao: briefing vazio nao basta

Em workspace zerado, o primeiro briefing nao deveria ser chamado de briefing. Deveria ser sessao de arranque.

Objetivo:

1. descobrir o minimo de contexto
2. captar rotina, frentes e prioridades
3. mostrar valor cedo
4. evitar menu de acao em cima do nada

Em workspace existente, ai sim a primeira sessao pode ser mais proxima de briefing.

Resumo brutal:

1. workspace vazio pede exploracao guiada
2. workspace com conteudo pede leitura cuidadosa + briefing inicial

## 10. Plano de transicao

### 10.1. Fase 1

Documentar e fixar o contrato de topologia.

### 10.2. Fase 2

Ensinar `setup` a trabalhar com:

1. pasta nova
2. pasta existente
3. wrappers em modo de adocao

### 10.3. Fase 3

Mover o layout gerado de flat para:

1. raiz minima
2. `/Prumo/`
3. `/.prumo/`

### 10.4. Fase 4

Introduzir overlay de customizacao:

1. `/Prumo/Custom/`
2. resolucao `custom > system`

### 10.5. Fase 5

Migrar workspaces existentes sem vandalismo:

1. backups claros
2. relatorio do que mudou
3. zero sumico silencioso

## 11. Criterio de pronto deste slice

Este slice so fecha quando:

1. o runtime parar de despejar memoria viva e estado tecnico na mesma raiz;
2. o `setup` oferecer escolha real entre pasta nova e pasta existente;
3. wrappers existentes tiverem politica de adocao segura;
4. customizacao do usuario tiver camada imune a update;
5. a primeira sessao deixar de parecer briefing de apartamento vazio.
