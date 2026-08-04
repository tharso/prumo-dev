#!/usr/bin/env node
/**
 * Builder do `decidir` (#321): cards.json → HTML final.
 *
 * Por que existe: não havia um "preencher template" barato. Cada briefing
 * com despacho visual escrevia um gerador do zero (o de 03/08 tinha 22 KB
 * — o maior bloco único de tempo do briefing) para fazer substituição de
 * strings num template que JÁ tem marcadores de injeção. Este arquivo é o
 * executor fixo dessa substituição: o agente autora DADOS, não código.
 *
 * O contrato de autoria é JSON ESTRITO (`prumo_decidir_cards.v1`) — a
 * alternativa que a #287 adiou como decisão de produto, tomada na #321.
 * `JSON.parse` não conhece comentário, regex nem função: a classe de
 * fragilidade do extrator do validador morre por construção no artefato
 * construído por aqui.
 *
 * O que ele NÃO faz: validar por conta própria. A régua dos cards vive no
 * `validate-cards.mjs` (#287) e o builder a executa via `validar()` — uma
 * fonte de verdade só. Reprovou, NÃO ESCREVE: artefato inválido não ganha
 * arquivo com cara de entregável.
 *
 *   node skills/decidir/build-cards.mjs <cards.json> <saida.html> [--json]
 *
 * Saída 0 = construído e validado; 1 = conteúdo reprovado (nada escrito);
 * 2 = não deu para processar (IO, JSON inválido, schema desconhecido).
 */

import { readFileSync, writeFileSync, realpathSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { validar } from "./validate-cards.mjs";

const SCHEMA = "prumo_decidir_cards.v1";

// Placeholders de HTML: substituição verbatim. A autoria é do agente — o
// mesmo modelo de confiança do preenchimento manual que isto substitui
// (#287: o artefato é do agente, não de terceiro).
const CAMPOS_HTML = {
  title: "__DOC_TITLE__",
  kicker: "__KICKER__",
  headline: "__HEADLINE__",
  meta: "__META__",
  intro: "__INTRO__",
  howto: "__HOWTO__",
  finale_title: "__FINALE_TITLE__",
  finale_text: "__FINALE_TEXT__",
  finale_hint: "__FINALE_HINT__",
};

// Estes dois vivem DENTRO de string JS de aspas simples no CONFIG do
// template. Entram COM as aspas, via JSON.stringify: apóstrofo ou quebra
// no valor não quebra mais o documento inteiro.
const CAMPOS_JS = {
  storage_key: "'__STORAGE_KEY__'",
  report_title: "'__REPORT_TITLE__'",
};

class ErroDeLeitura extends Error {} // exit 2 — não deu para processar
class ErroDeConteudo extends Error { // exit 1 — cards reprovados, nada escrito
  constructor(erros) {
    super(erros.join("; "));
    this.erros = erros;
  }
}

function carregarCards(path) {
  let bruto;
  try {
    bruto = readFileSync(path, "utf8");
  } catch (e) {
    throw new ErroDeLeitura(`não consegui ler ${path}: ${e.message}`);
  }
  let dados;
  try {
    dados = JSON.parse(bruto);
  } catch (e) {
    // O formato antigo dos exemplos ({id: 'x'}) é JS válido e JSON
    // inválido. A mensagem aponta a diferença em vez de só reclamar.
    throw new ErroDeLeitura(
      `${path} não é JSON estrito (chaves com aspas duplas, sem comentário, ` +
        `sem apóstrofo como delimitador): ${e.message}`,
    );
  }
  if (!dados || typeof dados !== "object" || Array.isArray(dados)) {
    throw new ErroDeLeitura(`${path} não é um objeto JSON`);
  }
  if (dados.schema !== SCHEMA) {
    throw new ErroDeLeitura(
      `schema '${dados.schema}' desconhecido — este builder fala ${SCHEMA}`,
    );
  }
  return dados;
}

// String.replace expande `$&`/`$'` no substituto — um card citando "$&"
// corromperia o documento em silêncio. split/join é imune por construção.
function substituir(html, token, valor) {
  return html.split(token).join(valor);
}

function montar(dados, template) {
  const erros = [];
  const doc = dados.doc;
  if (!doc || typeof doc !== "object" || Array.isArray(doc)) {
    throw new ErroDeConteudo(["'doc' é obrigatório e precisa ser objeto"]);
  }

  const campos = { ...CAMPOS_HTML, ...CAMPOS_JS };
  for (const campo of Object.keys(campos)) {
    if (typeof doc[campo] !== "string") {
      erros.push(
        `doc.${campo} é obrigatório e precisa ser string ` +
          `(preenche ${campos[campo].replace(/'/g, "")} no template)`,
      );
    }
  }

  const sections = Array.isArray(dados.sections) ? dados.sections : null;
  const points = Array.isArray(dados.points) ? dados.points : null;
  if (!sections) erros.push("'sections' é obrigatório e precisa ser lista");
  if (!points) erros.push("'points' é obrigatório e precisa ser lista");
  // O validador aprovaria o vazio (0 erros em 0 cards). Documento sem
  // card não decide nada — a guarda é daqui.
  if (sections && sections.length === 0) erros.push("'sections' está vazio");
  if (points && points.length === 0) {
    erros.push("'points' está vazio — documento sem decisão não sai");
  }
  if (erros.length) throw new ErroDeConteudo(erros);

  let html = template;
  for (const [campo, token] of Object.entries(CAMPOS_HTML)) {
    if (!html.includes(token)) erros.push(`template sem o placeholder ${token}`);
    html = substituir(html, token, doc[campo]);
  }
  for (const [campo, token] of Object.entries(CAMPOS_JS)) {
    if (!html.includes(token)) erros.push(`template sem o placeholder ${token}`);
    html = substituir(html, token, JSON.stringify(String(doc[campo])));
    // O comentário-documentação do template cita estes dois SEM aspas
    // ("Placeholders do corpo: __STORAGE_KEY__ …"). Segunda passada na
    // forma nua, simétrica ao que já acontece com os 9 de HTML — senão o
    // artefato final sai com token cru no cabeçalho.
    html = substituir(html, token.slice(1, -1), doc[campo]);
  }

  // Resíduo conferido ANTES da injeção de dados: neste ponto, token
  // sobrando só pode ser substituição que falhou — conteúdo de card ainda
  // não entrou, então não há falso positivo possível.
  for (const token of Object.values(CAMPOS_HTML)) {
    if (html.includes(token)) erros.push(`${token} sobrou após a substituição`);
  }
  for (const token of Object.values(CAMPOS_JS)) {
    if (html.includes(token.slice(1, -1))) {
      erros.push(`${token.slice(1, -1)} sobrou após a substituição`);
    }
  }
  if (erros.length) throw new ErroDeConteudo(erros);

  for (const [marcador, lista] of [
    ["/*__SECTIONS__*/", sections],
    ["/*__POINTS__*/", points],
  ]) {
    if (!html.includes(marcador)) {
      throw new ErroDeConteudo([`template sem o marcador ${marcador}`]);
    }
    const injecao = lista.map((item) => "  " + JSON.stringify(item)).join(",\n");
    html = substituir(html, marcador, injecao);
  }

  return html;
}

function main(argv) {
  const json = argv.includes("--json");
  const args = argv.filter((a) => a !== "--json");
  if (args.length !== 2) {
    console.error("uso: node build-cards.mjs <cards.json> <saida.html> [--json]");
    return 2;
  }
  const [origem, destino] = args;

  const emitir = (payload, humano) => {
    if (json) console.log(JSON.stringify(payload, null, 2));
    else console.log(humano);
  };

  let html;
  let veredito;
  try {
    const template = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "assets", "template.html"),
      "utf8",
    );
    const dados = carregarCards(origem);
    html = montar(dados, template);
    veredito = validar(html);
  } catch (e) {
    if (e instanceof ErroDeConteudo) {
      emitir(
        { ok: false, erros: e.erros, total: null, renderizaveis: null, saida: null },
        `REPROVADO — ${e.erros.length} problema(s):\n` +
          e.erros.map((x) => `  • ${x}`).join("\n"),
      );
      return 1;
    }
    if (e instanceof ErroDeLeitura || e?.constructor?.name === "ErroDeLeitura") {
      // A segunda checagem cobre o ErroDeLeitura do validate-cards.mjs
      // (classe própria daquele módulo): um HTML que o validador nem
      // consegue LER é bug do builder, não dos cards.
      console.error(`não deu para construir: ${e.message}`);
      return 2;
    }
    throw e;
  }

  if (!veredito.ok) {
    emitir(
      { ...veredito, saida: null },
      `REPROVADO — ${veredito.erros.length} problema(s):\n` +
        veredito.erros.map((x) => `  • ${x}`).join("\n"),
    );
    return 1;
  }

  try {
    writeFileSync(destino, html, "utf8");
  } catch (e) {
    console.error(`não consegui escrever ${destino}: ${e.message}`);
    return 2;
  }
  emitir(
    { ...veredito, saida: destino },
    `ok — ${veredito.total} cards, ${veredito.renderizaveis} renderizáveis → ${destino}`,
  );
  return 0;
}

// Mesma guarda do validador: importar este módulo não executa o main, e a
// comparação de caminho sobrevive a symlink (/tmp → /var no macOS).
function _mesmoArquivo(a, b) {
  try {
    return realpathSync(a) === realpathSync(b);
  } catch {
    return resolve(a) === resolve(b);
  }
}

if (process.argv[1] && _mesmoArquivo(fileURLToPath(import.meta.url), process.argv[1])) {
  process.exit(main(process.argv.slice(2)));
}
