#!/usr/bin/env node
/**
 * Validador do HTML gerado pelo `decidir` (#287).
 *
 * Por que existe: a instrução antiga mandava contar "nº de <article
 * class='card'> RENDERIZADOS". Essa string aparece UMA vez no arquivo, dentro
 * do template literal de `cardHTML` — um grep devolve 1 com 29 cards ou com
 * zero. Lida ao pé da letra, ela embute execução de JS, e foi por isso que o
 * braço do browser pareceu obrigatório: um briefing real gastou 186 segundos
 * instalando Chromium para conferir 29 cards.
 *
 * A fronteira útil não é "estático vs. headless" — é "com ou sem motor JS".
 * E o defeito nomeado (tag crua engolindo os cards seguintes) tem causa
 * conhecida: um `<` não escapado num campo de markup. Validar os campos
 * contra uma allowlist torna o engolimento IMPOSSÍVEL, em vez de detectá-lo
 * depois de pintar pixels.
 *
 * Não renderiza, não abre rede, não instala nada. Roda os literais num
 * sandbox `vm` sem `process` nem `require`.
 *
 *   node skills/decidir/validate-cards.mjs <arquivo.html> [--json]
 *
 * Saída 0 = aprovado, 1 = reprovado, 2 = não deu para ler.
 */

import { readFileSync } from "node:fs";
import { createContext, runInContext } from "node:vm";

// Campos que o template interpola SEM escapar (`template.html:528-610`) e que
// portanto carregam markup do gerador. É onde a tag crua entra.
const CAMPOS_MARKUP = ["contexto", "evidencia", "proposta", "sugestao"];
// Campos que o template interpola sem escapar mas que são rótulo, não prosa:
// markup neles nunca é intencional.
const CAMPOS_TEXTO_PURO = ["title", "id", "sec", "type"];

// Allowlist deliberadamente pequena. `exemplos-de-cards.md` usa `<span
// class="ref">` e `<span class="q">` legitimamente — banir todo `<` reprovaria
// o exemplo canônico do próprio produto.
const TAGS_PERMITIDAS = new Map([
  ["span", new Set(["ref", "q"])],
  ["br", new Set()],
  ["strong", new Set()],
  ["em", new Set()],
]);

const TIPOS_VALIDOS = new Set(["despacho", "escolha"]);

class ErroDeLeitura extends Error {}

function extrairLiteral(html, marcador) {
  // O template injeta em `const X = [ /*__MARCADOR__*/ ];`
  const abre = new RegExp(`const\\s+${marcador}\\s*=\\s*\\[`);
  const m = abre.exec(html);
  if (!m) throw new ErroDeLeitura(`não achei o literal ${marcador}`);

  let i = m.index + m[0].length - 1;
  let profundidade = 0;
  let dentroDeString = null;
  for (; i < html.length; i++) {
    const c = html[i];
    if (dentroDeString) {
      if (c === "\\") i++;
      else if (c === dentroDeString) dentroDeString = null;
      continue;
    }
    if (c === "'" || c === '"' || c === "`") dentroDeString = c;
    else if (c === "[") profundidade++;
    else if (c === "]") {
      profundidade--;
      if (profundidade === 0) return html.slice(m.index + m[0].length - 1, i + 1);
    }
  }
  throw new ErroDeLeitura(`literal ${marcador} não fecha`);
}

function avaliar(literal, marcador) {
  // Sandbox sem `process`, `require`, `globalThis` útil ou timers: o arquivo
  // é gerado pelo agente, mas avaliar código de um artefato merece cinto.
  const ctx = createContext(Object.create(null));
  try {
    const valor = runInContext(`(${literal})`, ctx, { timeout: 1000 });
    if (!Array.isArray(valor)) throw new ErroDeLeitura(`${marcador} não é lista`);
    return valor;
  } catch (e) {
    if (e instanceof ErroDeLeitura) throw e;
    // SyntaxError aqui é o que o `node --check` pegaria — com linha e coluna.
    throw new ErroDeLeitura(`${marcador} não avalia: ${e.message}`);
  }
}

function tagsDe(texto) {
  const achadas = [];
  const re = /<\s*\/?\s*([a-zA-Z][\w-]*)([^>]*)>/g;
  let m;
  while ((m = re.exec(texto)) !== null) {
    achadas.push({ nome: m[1].toLowerCase(), atributos: m[2] || "", bruto: m[0] });
  }
  return achadas;
}

function classesDe(atributos) {
  const m = /class\s*=\s*["']([^"']*)["']/.exec(atributos);
  return m ? m[1].trim().split(/\s+/).filter(Boolean) : [];
}

function validarMarkup(valor, campo, id, erros) {
  if (typeof valor !== "string") return;

  // `<` solto (comparação, "a < b") também engole o resto do card no parser
  // do browser — é o mesmo defeito, sem parecer tag.
  const soltos = valor.match(/<(?![a-zA-Z/])/g);
  if (soltos) {
    erros.push(
      `card ${id}: '<' não escapado em '${campo}' — escreva &lt;. ` +
        `É assim que uma tag crua engole os cards seguintes.`,
    );
  }

  for (const { nome, atributos, bruto } of tagsDe(valor)) {
    if (!TAGS_PERMITIDAS.has(nome)) {
      erros.push(
        `card ${id}: tag <${nome}> não permitida em '${campo}' (${bruto.slice(0, 40)}). ` +
          `Permitidas: ${[...TAGS_PERMITIDAS.keys()].join(", ")}. ` +
          `Texto de terceiro vai em conteudo_b64, não aqui.`,
      );
      continue;
    }
    const permitidas = TAGS_PERMITIDAS.get(nome);
    for (const classe of classesDe(atributos)) {
      if (!permitidas.has(classe)) {
        erros.push(
          `card ${id}: classe '${classe}' não permitida em <${nome}> ('${campo}')`,
        );
      }
    }
  }
}

function validarTextoPuro(valor, campo, id, erros) {
  if (typeof valor !== "string") return;
  if (/[<>]/.test(valor)) {
    erros.push(`card ${id}: '${campo}' é texto puro e contém '<' ou '>' — escape`);
  }
}

function validarBase64(valor, id, erros) {
  if (valor === undefined || valor === null) return;
  if (typeof valor !== "string") {
    erros.push(`card ${id}: conteudo_b64 não é string`);
    return;
  }
  if (/\s/.test(valor)) {
    erros.push(
      `card ${id}: conteudo_b64 tem espaço ou quebra de linha — o base64 do ` +
        `GNU quebra em 76 colunas e vira SyntaxError; use tr -d '\\r\\n'`,
    );
    return;
  }
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(valor)) {
    erros.push(`card ${id}: conteudo_b64 fora do alfabeto base64`);
  }
}

export function validar(html) {
  const secoes = avaliar(extrairLiteral(html, "SECTIONS"), "SECTIONS");
  const pontos = avaliar(extrairLiteral(html, "POINTS"), "POINTS");

  const erros = [];
  const idsDeSecao = new Set();
  for (const s of secoes) {
    if (!s || typeof s.id !== "string") {
      erros.push("seção sem id string");
      continue;
    }
    if (idsDeSecao.has(s.id)) erros.push(`seção duplicada: '${s.id}'`);
    idsDeSecao.add(s.id);
  }

  const vistos = new Set();
  let renderizaveis = 0;

  for (const p of pontos) {
    const id = p && p.id !== undefined ? String(p.id) : "(sem id)";

    if (!p || typeof p !== "object") {
      erros.push("entrada de POINTS não é objeto");
      continue;
    }
    if (p.id === undefined || p.id === null || String(p.id) === "") {
      erros.push("card sem id");
    } else if (vistos.has(String(p.id))) {
      // Dois cards com o mesmo id: o segundo sobrescreve o estado do
      // primeiro no localStorage e o despacho vira loteria.
      erros.push(`id duplicado: '${p.id}'`);
    } else {
      vistos.add(String(p.id));
    }

    if (!TIPOS_VALIDOS.has(p.type)) {
      erros.push(`card ${id}: type '${p.type}' inválido (use despacho ou escolha)`);
    }

    // O silêncio mais caro: `if (!pts.length) return;` no render faz o card
    // de seção inexistente sumir sem erro e sem console.
    if (!idsDeSecao.has(p.sec)) {
      erros.push(
        `card ${id}: sec '${p.sec}' não existe em SECTIONS — o card some ` +
          `em SILÊNCIO no render, sem erro e sem console`,
      );
    } else {
      renderizaveis++;
    }

    for (const campo of CAMPOS_MARKUP) validarMarkup(p[campo], campo, id, erros);
    for (const campo of CAMPOS_TEXTO_PURO) validarTextoPuro(p[campo], campo, id, erros);
    validarBase64(p.conteudo_b64, id, erros);

    for (const b of p.badges || []) validarTextoPuro(b?.label, "badges[].label", id, erros);

    const chaves = new Set();
    for (const a of p.actions || []) {
      if (!a || typeof a.key !== "string") {
        erros.push(`card ${id}: ação sem key`);
        continue;
      }
      if (chaves.has(a.key)) erros.push(`card ${id}: ação '${a.key}' repetida`);
      chaves.add(a.key);
      validarTextoPuro(a.label, `actions[${a.key}].label`, id, erros);
    }

    const opcoes = new Set();
    for (const o of p.options || []) {
      if (!o || typeof o.key !== "string") {
        erros.push(`card ${id}: opção sem key`);
        continue;
      }
      if (opcoes.has(o.key)) erros.push(`card ${id}: opção '${o.key}' repetida`);
      opcoes.add(o.key);
      validarTextoPuro(o.label, `options[${o.key}].label`, id, erros);
      validarTextoPuro(o.desc, `options[${o.key}].desc`, id, erros);
    }
  }

  return { ok: erros.length === 0, erros, total: pontos.length, renderizaveis };
}

function main(argv) {
  const args = argv.filter((a) => a !== "--json");
  const json = argv.includes("--json");
  if (args.length !== 1) {
    console.error("uso: node validate-cards.mjs <arquivo.html> [--json]");
    return 2;
  }

  let html;
  try {
    html = readFileSync(args[0], "utf8");
  } catch (e) {
    console.error(`não consegui ler ${args[0]}: ${e.message}`);
    return 2;
  }

  let r;
  try {
    r = validar(html);
  } catch (e) {
    if (e instanceof ErroDeLeitura) {
      console.error(`não deu para validar: ${e.message}`);
      return 2;
    }
    throw e;
  }

  if (json) {
    console.log(JSON.stringify(r, null, 2));
  } else if (r.ok) {
    console.log(`ok — ${r.total} cards, ${r.renderizaveis} renderizáveis`);
  } else {
    console.log(`REPROVADO — ${r.erros.length} problema(s):`);
    for (const e of r.erros) console.log(`  • ${e}`);
  }
  return r.ok ? 0 : 1;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  process.exit(main(process.argv.slice(2)));
}
