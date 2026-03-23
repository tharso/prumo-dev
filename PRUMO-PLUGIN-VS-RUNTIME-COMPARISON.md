# Prumo Plugin do Cowork vs Runtime Atual

> Documento de referência para objetivo de produto.
>
> Comparação entre:
> 1. a experiência legada do **Prumo Plugin do Cowork** (tomando a linha `4.16.1` como fotografia final conhecida do modelo acoplado ao host);
> 2. o **Prumo Runtime atual** (`4.16.2`), já no trilho local-first, cross-host e com estrutura pronta para workflows.

## 1. Aviso antes da comparação

Esta comparação não é perfeitamente simétrica.

O plugin legado era uma mistura de:

1. produto;
2. host;
3. UX conversacional;
4. automações locais;
5. skills e rituais do Cowork.

O runtime atual já separa essas camadas. Então a pergunta útil não é:

“O runtime novo é idêntico ao plugin velho?”

A pergunta útil é:

“O runtime novo consegue recuperar a **qualidade percebida** do plugin velho sem voltar a depender da mesma gambiarra arquitetural?”

Essa, sim, é a pergunta que presta.

## 2. Tese central

O plugin antigo era mais fluido.

O runtime atual é mais sólido.

O objetivo do produto não deve ser voltar ao plugin. Deve ser isto:

**recuperar a fluidez do legado em cima da arquitetura nova, não trocar a arquitetura nova por nostalgia operacional.**

Voltar ao acoplamento do Cowork para resgatar conforto seria como demolir uma casa de alvenaria porque a barraca antiga tinha mais sombra. Faz carinho na memória e sabota o futuro.

## 3. Comparação detalhada

| Dimensão | Plugin do Cowork (linha legada ~4.16.1) | Runtime atual (4.16.2) | Ganhamos | Perdemos / Gap | Objetivo correto |
|---|---|---|---|---|---|
| Natureza do produto | Produto e host vinham embaralhados | Produto virou runtime próprio com contrato explícito | Clareza de arquitetura | Perda de “mágica embutida” | Fazer o runtime parecer produto pronto, não framework em exposição |
| Dependência do host | Altíssima. Cowork era quase o corpo inteiro | Menor. Host virou adapter | Portabilidade real | Mais atrito de UX em hosts medianos | Manter desacoplamento e polir adapters bons |
| Porta de entrada | Slash commands e hábitos do Cowork faziam muito do trabalho | `Prumo`, `prumo`, `start --format json`, `briefing --format json` | Contrato explícito | Alguns hosts ainda tropeçam na invocação curta | Invocação curta confiável em Antigravity, Codex e Claude Code |
| Briefing | Mais orgânico, com sensação de copiloto | Mais estruturado, claro e testável | Melhor observabilidade | Menos calor humano em parte dos testes | Briefing com a estrutura nova e a sensação de parceria antiga |
| Tom da conversa | Mais natural, menos “saída de sistema” | Melhorou, mas ainda alterna entre produto e relatório | Base controlável | Ainda falta cadência e ritmo do legado | Conversa com menos cardápio e mais condução |
| Proatividade | Forte, às vezes quase invisível | Explícita, rastreável e ainda mais tímida | Menos telepatia falsa | Menos “parece que ele já sabe” | Proatividade de alto sinal, sem chute escondido |
| Continuação de trabalho | Existia mais no costume do plugin | Existe no contrato do runtime e em `actions[]` | Continuação virou first-class | Ainda precisa de mais fluidez operacional | Host continuar trabalho sem improvisar produto |
| Documentação viva | Acontecia, mas muito puxada pelo host | Está formalizada no produto | Pauta/Inbox/Registro/Workflows entraram no núcleo | Alguns hosts escrevem demais ou no formato errado | Atualizar documentação certa, do jeito certo, com intervenção mínima |
| Inbox mobile | Preview e triagem existiam de fato | Agora também existe CLI canônica de preview | Gap conceitual fechado | Ainda falta integrar isso melhor à conversa dos hosts | Preview e triagem virarem rotina de operador, não truque lateral |
| Skills e módulos | Muito valor estava embutido no ecossistema do Cowork | Viraram referência, contrato e governança | Menos dependência de store/plugin | Parte da riqueza operacional ainda não foi portada integralmente | Reencarnar o valor das skills no runtime, não no teatro do host |
| Qualidade subjetiva | Alta quando o Cowork colaborava | Variável conforme host | Mais controle técnico | Menor consistência emocional | Trazer de volta a sensação de “isso me ajuda de verdade hoje” |
| Integrações locais | Muito ligadas ao ambiente do macOS e do host | Providers explícitos por capability | Arquitetura mais limpa | Algumas integrações viraram backlog | Deixar integração complementar sem sequestrar o produto |
| Cross-platform | Na prática, macOS e Cowork no centro | Mac e Windows entraram no desenho real | Expansão comercial séria | Windows ainda está no trilho mínimo | Windows funcional sem pedir perdão o tempo inteiro |
| Testabilidade | Mais frágil, mais implícita | Melhor cobertura, smoke, CI e contrato | Confiabilidade de release | Teste verde não cria charme sozinho | Usar a base sólida para recuperar UX, não parar nela |
| Update / release | Plugin, marketplace, host e estado se misturavam | Runtime, manifests e core estão mais governados | Menos drift invisível | Ainda há custo de sincronização | Release limpa e previsível |
| Estratégia de host | Cowork era centro gravitacional | Antigravity lidera, Codex referencia, Claude secundário | Estratégia menos provinciana | Cowork deixou de ser muleta | Tratar host como distribuição, não como produto |
| Estrutura para workflows | Intuição forte, estrutura implícita | Estrutura explícita em `WORKFLOWS.md` | Fundação melhor | Ainda sem workflows verticais concretos | Fase seguinte: workflows reais em cima dessa fundação |
| Comercialmente | Demo brilhava dentro do Cowork | Produto é mais defendível fora dele | Menos “feature de app”, mais produto | Precisa recuperar brilho de UX | Piloto comercial forte em Antigravity sem depender de nostalgia |

## 4. O que foi ganho de verdade

Não o que soa bonito. O que foi ganho de verdade.

### 4.1. Produto deixou de morar de aluguel dentro do Cowork

Antes, parte demais do valor do Prumo vinha da convivência íntima com o host. Isso dava fluidez, mas também deixava o produto vulnerável ao humor do plugin store, à sandbox, ao slash command e ao tipo de drama operacional que envelhece mal.

Hoje, o Prumo tem:

1. runtime próprio;
2. contrato explícito para host;
3. saídas estruturadas;
4. separação entre core, adapter, provider e documentação viva.

Isso não deixa o produto mais sexy por si só. Deixa menos refém. E isso vale dinheiro.

### 4.2. O produto começou a pensar além do briefing

No legado, o briefing era o palco principal e quase sempre também o cenário.

No runtime atual, já existe estrutura explícita para:

1. continuação;
2. organização do dia;
3. triagem de inbox;
4. documentação viva;
5. scaffolding de workflows.

Esse é o movimento certo. Se o produto ficar só no “briefing bem escrito”, ele vira jornalzinho premium. Útil por cinco minutos. Substituível em três meses.

### 4.3. Windows entrou na conversa séria

Não como slide de pitch. Como requisito real.

Isso muda a natureza do produto:

1. menos dependência implícita de macOS;
2. necessidade de providers por capability;
3. necessidade de degradação honesta quando uma integração não existe naquela plataforma.

É um ganho estrutural importante. Também é onde o romantismo técnico costuma morrer afogado, o que não é necessariamente ruim.

## 5. O que foi perdido de verdade

Aqui mora o que dói. E convém olhar para isso sem perfume.

### 5.1. Fluidez conversacional

O plugin do Cowork, quando tudo encaixava, parecia mais vivo.

Ele:

1. conduzia melhor;
2. perguntava menos o óbvio;
3. fazia mais com menos cerimônia;
4. parecia mais parceiro do que painel administrativo.

O runtime atual ainda está recuperando isso.

### 5.2. Sensação de “copiloto diário”

O legado acertava mais a sensação de que o Prumo:

1. sabia onde você estava no dia;
2. puxava a próxima alavanca com menos formalidade;
3. misturava contexto, organização e execução com menos cara de protocolo.

Hoje, parte disso foi substituída por estrutura. Necessária, sim. Suficiente, não.

### 5.3. Riqueza operacional embutida nas skills

O plugin antigo carregava valor em skills, scripts e micro-hábitos que estavam muito próximos da experiência do host.

Ao migrar para runtime:

1. parte desse valor virou módulo e referência;
2. parte virou contrato explícito;
3. parte ainda não voltou como experiência concreta.

Esse terceiro pedaço é o mais importante.

## 6. Onde o gap está hoje

O gap real não está mais em “falta de comando”.

Essa fase do projeto já melhorou bastante.

O gap agora está em cinco lugares:

### 6.1. Orquestração conversacional

O runtime já sabe mais coisas.
Mas nem sempre sabe **entrar em cena** do jeito certo.

Sintoma:

1. ainda há respostas que parecem menu;
2. ainda há host que faz pose antes de trabalhar;
3. ainda há momento em que o produto informa melhor do que conduz.

### 6.2. Disciplina dos hosts

Alguns hosts respeitam o runtime.
Outros tentam ser autores, padres e inventores de comando ao mesmo tempo.

Hoje:

1. `Codex` já provou maturidade boa;
2. `Antigravity` é o host comercialmente mais promissor;
3. `Claude Code` é útil, mas ainda irregular;
4. `Cowork` ficou fora da linha de frente;
5. `Gemini CLI` foi mal.

Então a qualidade do Prumo já depende menos do produto e mais da superfície em que ele cai. Isso é problema de adapter, não de essência do produto. Mas continua sendo problema.

### 6.3. Atualização documental com mão leve

O Prumo precisa:

1. atualizar documentação viva;
2. não reescrever arquivo inteiro sem necessidade;
3. não impor formato autoral do host;
4. deixar rastro útil e proporcional.

Esse equilíbrio ainda está em formação.

### 6.4. Priorização com mais inteligência e menos cardápio

O legado, no seu melhor momento, não parecia só exibir opções. Parecia já te colocar com a mão na maçaneta certa.

O runtime atual melhorou nisso, mas ainda cai em:

1. enumerar demais;
2. conduzir de menos;
3. hesitar quando poderia liderar.

### 6.5. Conversa + execução + documentação na mesma passada

Esse é o coração do valor.

Não basta:

1. falar bem;
2. rodar comando;
3. gerar arquivo.

O Prumo bom faz as três coisas parecerem uma só passada de mão.

É esse efeito que ainda estamos recompondo.

## 7. Então: chegar na fluidez antiga é factível?

### Resposta curta

**Sim, é factível.**

Mas com uma condição importante:

**não é factível recuperar a fluidez antiga copiando o arranjo antigo.**

Se tentarmos recuperar a sensação antiga reinstalando o mesmo acoplamento ao Cowork, vamos reconstruir o conforto junto com a fragilidade. É trocar coluna por cortina.

### Resposta longa

Se por “fluidez” você quer dizer:

1. menos fricção para começar;
2. melhor condução;
3. mais proatividade de alto sinal;
4. documentação útil saindo no mesmo movimento;
5. sensação de copiloto diário;
6. menos cheiro de sistema e mais cheiro de parceria;

então sim, isso é alcançável.

Se por “fluidez” você quer dizer:

1. dependência íntima do Cowork;
2. uso de truques implícitos do host;
3. magia local específica daquele ecossistema;
4. comportamento que só funciona bem onde nasceu;

então não. E ainda bem.

## 8. O que precisa acontecer para isso virar verdade

### 8.1. O briefing precisa voltar a conduzir

Não basta ser correto.

Precisa:

1. ler o estado do dia;
2. escolher melhor a próxima jogada;
3. falar menos como menu;
4. soar menos como dump e mais como operador.

### 8.2. Continuação tem que ficar mais afiada

Hoje ela já existe no contrato.

Agora precisa ganhar:

1. melhor senso de oportunidade;
2. prompts mais executáveis;
3. menos espaço para o host improvisar;
4. mais qualidade na atualização de documentação.

### 8.3. A documentação viva precisa ficar mais elegante

O Prumo não pode agir como alguém que entra na cozinha, faz o almoço e troca os armários de lugar.

Ele precisa:

1. editar menos;
2. registrar melhor;
3. deixar mais claro o que veio do inbox, o que virou pauta, o que virou ideia e o que virou decisão.

### 8.4. Os melhores fluxos do legado precisam ser reencarnados como runtime

Não como saudade.

Como capacidade nativa:

1. inbox preview;
2. triagem;
3. retomada de frente quente;
4. organização do dia;
5. registro de candidatos a workflow.

Esse trabalho já começou. Ainda não terminou.

### 8.5. Antigravity precisa virar demo boa de produto, não só host obediente

Esse é o trilho comercial.

A régua ali não é:

“rodou o comando?”

A régua é:

“pareceu um assistente que realmente alivia o dia?”

## 9. Objetivo de produto que este documento fixa

O objetivo não é:

1. reconstituir o plugin do Cowork;
2. imitar byte por byte a UX antiga;
3. voltar a depender do host para parecer bom.

O objetivo é:

1. manter a arquitetura nova;
2. manter o runtime local-first;
3. manter o desenho cross-platform;
4. manter adapters explícitos por host;
5. recuperar a sensação de fluidez, parceria e utilidade concreta que o legado tinha no seu melhor momento.

Em uma frase:

**o objetivo é fazer o runtime novo parecer tão vivo quanto o plugin velho, sem voltar a morar dentro do plugin velho.**

## 10. Critérios de aceite para dizer “recuperamos a fluidez”

Só deveríamos dizer isso quando, em teste real:

1. o usuário chama `Prumo` e a entrada é quase sem atrito;
2. o briefing não parece cardápio burocrático;
3. a proposta do dia é útil e específica;
4. a continuação leva a trabalho real, não só a mais conversa;
5. `PAUTA.md`, `INBOX.md`, `REGISTRO.md` e `WORKFLOWS.md` melhoram de forma proporcional e clara;
6. o host não inventa produto;
7. o usuário termina a sessão sentindo que o dia ficou menos pegajoso.

Se esses sete pontos não acontecerem juntos, ainda não recuperamos a fluidez. Recuperamos pedaços.

## 11. Veredito

O plugin do Cowork estava mais perto do **efeito emocional certo**.

O runtime atual está mais perto da **forma técnica certa**.

O trabalho da próxima fase é juntar essas duas coisas sem voltar a casar produto com host.

É factível.

Mas não será uma consequência automática da arquitetura nova.
Será um trabalho deliberado de UX, priorização, texto, continuidade e disciplina de adapter.

O lado bom é que agora o problema está mais honesto.

Antes, a fluidez vinha misturada com fragilidade.
Agora, a fragilidade está menor e a fluidez virou alvo explícito.

Finalmente estamos tentando construir um barco, em vez de continuar lustrando o cais.
