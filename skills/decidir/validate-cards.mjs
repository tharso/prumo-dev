#!/usr/bin/env node
/**
 * Validador do HTML gerado pelo `decidir` (#287).
 *
 * Por que existe: a instrução antiga mandava contar "nº de <article
 * class='card'> RENDERIZADOS". Essa string aparece UMA vez no arquivo, dentro
 * do template literal de `cardHTML` — um grep devolve 1 com 29 cards ou com
 * zero. Lida ao pé da letra, ela embutia execução de JS, e foi por isso que o
 * braço do browser pareceu obrigatório: um briefing real gastou 186 segundos
 * instalando Chromium para conferir 29 cards.
 *
 * A troca de fundo é atacar a CAUSA. O engolimento vem de um `<` que o
 * browser lê como tag num campo interpolado sem escape. Validado o campo, o
 * engolimento não acontece — não há sintoma para contar depois.
 *
 * O que ele NÃO é: uma fronteira de segurança. `node:vm` não é sandbox (a
 * própria doc do Node diz isso). O artefato é escrito pelo agente, não por
 * terceiro; o `vm` aqui reduz acidente, não hostilidade. Contra getter e
 * proxy — que rodariam FORA do timeout, na hora de ler o campo — os dados
 * atravessam `JSON.stringify` ainda dentro do contexto, e o que sai é dado
 * inerte.
 *
 *   node skills/decidir/validate-cards.mjs <arquivo.html> [--json]
 *
 * Saída 0 = aprovado, 1 = reprovado, 2 = não deu para ler.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { createContext, runInContext } from "node:vm";

// ── Contexto de destino de cada campo ────────────────────────────────────
// O template interpola SEM escape em dois lugares diferentes, e a regra muda
// conforme o destino. Confundir os dois foi o furo da primeira versão:
// proibir `<`/`>` não impede `id: 'x" onclick="..."'`, que quebra o ATRIBUTO.

// Vão parar dentro de aspas de atributo (data-pt, data-key, id, class, href).
const CAMPOS_ATRIBUTO = {
  point: ["id", "sec"],
  section: ["id"],
  badge: ["tone"],
  action: ["key", "tone"],
  option: ["key"],
};

// Texto visível que aceita markup leve do gerador.
const CAMPOS_MARKUP = ["contexto", "evidencia", "proposta", "sugestao"];

// Texto visível sem markup nenhum.
const CAMPOS_TEXTO = {
  point: ["title"],
  section: ["title", "sub", "num"],
  badge: ["label"],
  action: ["label", "requires"],
  option: ["label", "desc"],
};

// Identificador que pode entrar em atributo sem escape: sem aspas, sem `<`,
// `>`, `&`, espaço ou barra. `#sec-${id}` também vira href, então nada de `#`.
const ID_SEGURO = /^[A-Za-z0-9_.:-]+$/;
const TONES = new Set(["green", "amber", "red", "blue", "purple", "slate"]);
const TIPOS_VALIDOS = new Set(["despacho", "escolha"]);

// Gramática pequena e fechada. `exemplos-de-cards.md` usa `<span class="ref">`
// e `<span class="q">`; banir todo `<` reprovaria a documentação do produto.
const GRAMATICA = {
  span: { atributos: { class: new Set(["ref", "q"]) }, fecha: true },
  strong: { atributos: {}, fecha: true },
  em: { atributos: {}, fecha: true },
  br: { atributos: {}, fecha: false },
};

class ErroDeLeitura extends Error {}

// ── Extração ─────────────────────────────────────────────────────────────

function extrairLiteral(html, marcador) {
  const abre = new RegExp(`const\\s+${marcador}\\s*=\\s*\\[`);
  const m = abre.exec(html);
  if (!m) throw new ErroDeLeitura(`não achei o literal ${marcador}`);

  const inicio = m.index + m[0].length - 1;
  let profundidade = 0;
  let str = null;
  for (let i = inicio; i < html.length; i++) {
    const c = html[i];
    if (str) {
      if (c === "\\") i++;
      else if (c === str) str = null;
      continue;
    }
    if (c === "'" || c === '"' || c === "`") str = c;
    else if (c === "[") profundidade++;
    else if (c === "]") {
      profundidade--;
      if (profundidade === 0) return html.slice(inicio, i + 1);
    }
  }
  throw new ErroDeLeitura(`literal ${marcador} não fecha`);
}

function avaliar(literal, marcador) {
  // O extrator conhece string, não comentário nem regex. Um `]` dentro de
  // `/* ... */` truncaria o literal — e o truncamento vira SyntaxError aqui,
  // ou seja, falha ALTA. O card não deve trazer comentário nem regex; se
  // trouxer, isto reprova em vez de validar metade em silêncio.
  const ctx = createContext(Object.create(null));
  try {
    // O `JSON.stringify` roda DENTRO do contexto e no MESMO timeout: getter
    // e proxy disparam aqui, não depois, quando o host lesse o campo.
    const bruto = runInContext(`JSON.stringify(${literal})`, ctx, { timeout: 2000 });
    const valor = JSON.parse(bruto);
    if (!Array.isArray(valor)) throw new ErroDeLeitura(`${marcador} não é lista`);
    return valor;
  } catch (e) {
    if (e instanceof ErroDeLeitura) throw e;
    throw new ErroDeLeitura(`${marcador} não avalia como dado: ${e.message}`);
  }
}

// ── Validações ───────────────────────────────────────────────────────────

function validarAtributo(valor, campo, onde, erros) {
  if (valor === undefined || valor === null) return;
  const s = String(valor);
  if (!ID_SEGURO.test(s)) {
    erros.push(
      `${onde}: '${campo}' vai para dentro de um ATRIBUTO sem escape e só ` +
        `aceita [A-Za-z0-9_.:-] — '${s.slice(0, 30)}' quebraria o HTML ` +
        `(aspas fecham o atributo e o resto vira código)`,
    );
  }
}

function validarTexto(valor, campo, onde, erros) {
  if (valor === undefined || valor === null) return;
  if (/[<>]/.test(String(valor))) {
    erros.push(`${onde}: '${campo}' é texto puro e contém '<' ou '>' — escape`);
  }
}

function validarTone(valor, onde, erros) {
  if (valor === undefined || valor === null) return;
  if (!TONES.has(String(valor))) {
    erros.push(`${onde}: tone '${valor}' fora do enum (${[...TONES].join(", ")})`);
  }
}

function validarMarkup(valor, campo, onde, erros) {
  if (valor === undefined || valor === null) return;
  const texto = String(valor);
  const pilha = [];
  let i = 0;

  while (i < texto.length) {
    const lt = texto.indexOf("<", i);
    if (lt === -1) break;

    const m = /^<\s*(\/?)\s*([A-Za-z][\w-]*)((?:[^<>"']|"[^"]*"|'[^']*')*)>/.exec(
      texto.slice(lt),
    );
    if (!m) {
      // `<` que não abre construção reconhecida: comparação ("a < b"), tag
      // sem fechar (`<strong`) ou aspas soltas. Todo caso engole o resto.
      erros.push(
        `${onde}: '<' não escapado em '${campo}' — escreva &lt;. ` +
          `É assim que uma tag crua engole os cards seguintes.`,
      );
      return;
    }

    const [bruto, barra, nome, attrs] = [m[0], m[1], m[2].toLowerCase(), m[3] || ""];
    const regra = GRAMATICA[nome];
    if (!regra) {
      erros.push(
        `${onde}: tag <${nome}> não permitida em '${campo}'. ` +
          `Permitidas: ${Object.keys(GRAMATICA).join(", ")}. ` +
          `Texto de terceiro vai em conteudo_b64, não aqui.`,
      );
      return;
    }

    if (barra) {
      if (!regra.fecha) erros.push(`${onde}: </${nome}> não existe`);
      else if (pilha.pop() !== nome) {
        erros.push(`${onde}: </${nome}> sem abertura correspondente em '${campo}'`);
        return;
      }
    } else {
      const permitidos = regra.atributos;
      const encontrados = [...attrs.matchAll(/([A-Za-z-]+)\s*=\s*"([^"]*)"/g)];
      const nus = attrs.replace(/([A-Za-z-]+)\s*=\s*"[^"]*"/g, "").trim();
      if (nus) {
        // Atributo sem aspas ou sinalizador solto: `class=ref`, `onclick=x`.
        erros.push(`${onde}: atributo mal formado em <${nome}> ('${nus.slice(0, 24)}')`);
        return;
      }
      for (const [, chave, valorAttr] of encontrados) {
        if (!(chave in permitidos)) {
          erros.push(
            `${onde}: atributo '${chave}' não permitido em <${nome}> — ` +
              `só ${Object.keys(permitidos).join(", ") || "nenhum"}. ` +
              `(handlers como onclick entram por aqui)`,
          );
          return;
        }
        if (!permitidos[chave].has(valorAttr)) {
          erros.push(
            `${onde}: <${nome} ${chave}="${valorAttr}"> fora da allowlist ` +
              `(${[...permitidos[chave]].join(", ")})`,
          );
        }
      }
      if (regra.fecha) pilha.push(nome);
    }
    i = lt + bruto.length;
  }

  if (pilha.length) {
    erros.push(`${onde}: tag <${pilha[pilha.length - 1]}> não fechada em '${campo}'`);
  }
}

function validarBase64(valor, onde, erros) {
  if (valor === undefined || valor === null) return;
  if (typeof valor !== "string") {
    erros.push(`${onde}: conteudo_b64 não é string`);
    return;
  }
  if (/\s/.test(valor)) {
    erros.push(
      `${onde}: conteudo_b64 tem espaço ou quebra de linha — o base64 do GNU ` +
        `quebra em 76 colunas e vira SyntaxError; use tr -d '\\r\\n'`,
    );
    return;
  }
  try {
    const bytes = Buffer.from(valor, "base64");
    if (bytes.toString("base64").replace(/=+$/, "") !== valor.replace(/=+$/, "")) {
      erros.push(`${onde}: conteudo_b64 não é base64 canônico (round-trip falhou)`);
    }
  } catch {
    erros.push(`${onde}: conteudo_b64 não decodifica`);
  }
}

export function validar(html) {
  const secoes = avaliar(extrairLiteral(html, "SECTIONS"), "SECTIONS");
  const pontos = avaliar(extrairLiteral(html, "POINTS"), "POINTS");

  const erros = [];
  const idsDeSecao = new Set();

  for (const [n, s] of secoes.entries()) {
    const onde = `seção ${s?.id ?? `#${n}`}`;
    if (!s || typeof s !== "object") {
      erros.push(`${onde}: não é objeto`);
      continue;
    }
    for (const campo of CAMPOS_ATRIBUTO.section) validarAtributo(s[campo], campo, onde, erros);
    for (const campo of CAMPOS_TEXTO.section) validarTexto(s[campo], campo, onde, erros);
    if (typeof s.id !== "string" || !s.id) erros.push(`${onde}: sem id string`);
    else if (idsDeSecao.has(s.id)) erros.push(`${onde}: id duplicado`);
    else idsDeSecao.add(s.id);
  }

  const vistos = new Set();
  let renderizaveis = 0;

  for (const p of pontos) {
    const onde = `card ${p && p.id !== undefined ? p.id : "(sem id)"}`;
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
      erros.push(`${onde}: type '${p.type}' inválido (use despacho ou escolha)`);
    }

    // O silêncio mais caro: `if (!pts.length) return;` no render faz o card
    // de seção inexistente sumir sem erro e sem console.
    if (!idsDeSecao.has(p.sec)) {
      erros.push(
        `${onde}: sec '${p.sec}' não existe em SECTIONS — o card some em ` +
          `SILÊNCIO no render, sem erro e sem console`,
      );
    } else {
      renderizaveis++;
    }

    for (const campo of CAMPOS_ATRIBUTO.point) validarAtributo(p[campo], campo, onde, erros);
    for (const campo of CAMPOS_TEXTO.point) validarTexto(p[campo], campo, onde, erros);
    for (const campo of CAMPOS_MARKUP) validarMarkup(p[campo], campo, onde, erros);
    validarBase64(p.conteudo_b64, onde, erros);

    for (const b of p.badges || []) {
      validarTone(b?.tone, `${onde} badge`, erros);
      for (const campo of CAMPOS_TEXTO.badge) validarTexto(b?.[campo], campo, onde, erros);
    }

    const chaves = new Set();
    for (const a of p.actions || []) {
      if (!a || typeof a.key !== "string") {
        erros.push(`${onde}: ação sem key`);
        continue;
      }
      if (chaves.has(a.key)) erros.push(`${onde}: ação '${a.key}' repetida`);
      chaves.add(a.key);
      for (const campo of CAMPOS_ATRIBUTO.action) validarAtributo(a[campo], campo, onde, erros);
      validarTone(a.tone, `${onde} ação ${a.key}`, erros);
      for (const campo of CAMPOS_TEXTO.action) validarTexto(a[campo], campo, onde, erros);
    }

    const opcoes = new Set();
    for (const o of p.options || []) {
      if (!o || typeof o.key !== "string") {
        erros.push(`${onde}: opção sem key`);
        continue;
      }
      if (opcoes.has(o.key)) erros.push(`${onde}: opção '${o.key}' repetida`);
      opcoes.add(o.key);
      for (const campo of CAMPOS_ATRIBUTO.option) validarAtributo(o[campo], campo, onde, erros);
      for (const campo of CAMPOS_TEXTO.option) validarTexto(o[campo], campo, onde, erros);
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

// Comparar `import.meta.url` cru com `process.argv[1]` falha em path com
// espaço ou `#`, e no Windows: o processo saía 0 sem validar nada.
if (process.argv[1] && resolve(fileURLToPath(import.meta.url)) === resolve(process.argv[1])) {
  process.exit(main(process.argv.slice(2)));
}
