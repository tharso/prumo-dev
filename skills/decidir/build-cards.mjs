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

// `</script>` dentro de um valor JSON fecha o <script> do template — o
// parser de HTML roda ANTES do de JS, então a sequência vale mesmo dentro
// de string. E o validador não polícia `link.href`, que carrega URL de
// terceiro (item de inbox): sem isto, o builder emitia artefato "aprovado"
// e executável (Codex, 321-r1). O escape < decodifica pro MESMO
// `<` no parse: dado idêntico, HTML cego pra tag.
function jsonParaScript(valor) {
  return JSON.stringify(valor).replace(/</g, "\\u003c");
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

  // O cabeçalho <!-- ... --> documenta os placeholders com os MESMOS
  // tokens do corpo. Valor NENHUM entra em comentário HTML — um `-->` no
  // valor fecharia o comentário e o resto viraria markup. Os tokens de lá
  // viram marcador fixo ANTES da substituição do corpo; o valor real já
  // vive no lugar certo (corpo/CONFIG).
  const fimCabecalho = html.indexOf("-->");
  if (fimCabecalho !== -1) {
    let cabecalho = html.slice(0, fimCabecalho);
    const nus = [
      ...Object.values(CAMPOS_HTML),
      ...Object.values(CAMPOS_JS).map((t) => t.slice(1, -1)),
    ];
    for (const token of nus) {
      cabecalho = substituir(cabecalho, token, "(preenchido pelo build-cards.mjs)");
    }
    html = cabecalho + html.slice(fimCabecalho);
  }

  // Substituição em UMA passada com callback: o texto que o callback
  // devolve nunca é re-lido pelo scanner (garantia da spec do replace),
  // então valor com cara de placeholder — ou de marcador — atravessa
  // intacto em vez de receber a substituição seguinte dentro de si
  // (Codex, 321-r2: doc.title = "__KICKER__" saía como o valor do
  // kicker, exit 0, corrupção silenciosa). Callback também não expande
  // `$&` — a proteção que o split/join dava, a função dá de graça.
  const valores = new Map();
  for (const [campo, token] of Object.entries(CAMPOS_HTML)) {
    valores.set(token, () => doc[campo]);
  }
  for (const [campo, token] of Object.entries(CAMPOS_JS)) {
    valores.set(token, () => jsonParaScript(String(doc[campo])));
  }
  valores.set("/*__SECTIONS__*/", () =>
    sections.map((s) => "  " + jsonParaScript(s)).join(",\n"),
  );
  valores.set("/*__POINTS__*/", () =>
    points.map((p) => "  " + jsonParaScript(p)).join(",\n"),
  );

  const nusJS = new Set(Object.values(CAMPOS_JS).map((t) => t.slice(1, -1)));
  const vistos = new Set();
  const RE_TOKENS =
    /'__STORAGE_KEY__'|'__REPORT_TITLE__'|\/\*__(?:SECTIONS|POINTS)__\*\/|__[A-Z][A-Z_]*__/g;
  html = html.replace(RE_TOKENS, (tok) => {
    const gera = valores.get(tok);
    if (!gera) {
      // Forma nua de token de string JS fora do cabeçalho é drift do
      // template; `__ASSIM__` e afins são documentação e ficam como estão.
      if (nusJS.has(tok)) erros.push(`${tok} fora de contexto de string JS no template`);
      return tok;
    }
    vistos.add(tok);
    return gera();
  });

  // Presença conferida pelo que a passada VIU, não por re-busca no
  // resultado — busca no resultado acusaria falso positivo quando um
  // valor legitimamente contém a string de um token.
  for (const esperado of valores.keys()) {
    if (!vistos.has(esperado)) erros.push(`template sem o placeholder ${esperado}`);
  }
  if (erros.length) throw new ErroDeConteudo(erros);

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
