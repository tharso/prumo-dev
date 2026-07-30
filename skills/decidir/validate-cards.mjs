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

import { readFileSync, realpathSync } from "node:fs";
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
  span: { atributos: { class: new Set(["ref", "q"]) }, exige: ["class"], fecha: true },
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

function _tipoDeTexto(valor, campo, onde, erros) {
  // `String({})` vira "[object Object]" e o template renderiza isso. Campo
  // presente com tipo errado é artefato quebrado, não detalhe (Codex, r11).
  if (typeof valor === "string") return true;
  erros.push(
    `${onde}: '${campo}' é ${Array.isArray(valor) ? "lista" : typeof valor}, ` +
      `não string — o template interpola direto e renderiza ` +
      `'[object Object]' ou o número sem formatação`,
  );
  return false;
}

function validarNumeroDeSecao(valor, onde, erros) {
  // ÚNICA exceção ao "texto é string": `sec.num` é o contador exibido no
  // cabeçalho e no índice, e os exemplos o escrevem como número. Deixar essa
  // tolerância no helper geral vazava para `title` e `contexto` (Codex, r12).
  if (valor === undefined || valor === null) {
    erros.push(`${onde}: 'num' é obrigatório`);
    return;
  }
  const ok =
    typeof valor === "string" || (typeof valor === "number" && Number.isFinite(valor));
  if (!ok) erros.push(`${onde}: 'num' precisa ser string ou número finito`);
  else if (/[<>]/.test(String(valor))) erros.push(`${onde}: 'num' contém '<' ou '>'`);
}

function validarTexto(valor, campo, onde, erros, obrigatorio = false) {
  if (valor === undefined || valor === null) {
    if (obrigatorio) erros.push(`${onde}: '${campo}' é obrigatório`);
    return;
  }
  if (!_tipoDeTexto(valor, campo, onde, erros)) return;
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

function validarMarkup(valor, campo, onde, erros, obrigatorio = false) {
  if (valor === undefined || valor === null) {
    if (obrigatorio) erros.push(`${onde}: '${campo}' é obrigatório`);
    return;
  }
  if (!_tipoDeTexto(valor, campo, onde, erros)) return;
  const texto = String(valor);
  const pilha = [];
  let i = 0;

  while (i < texto.length) {
    const lt = texto.indexOf("<", i);
    if (lt === -1) break;

    // Sem espaço entre `<` e o nome, nem entre `</` e o nome: `< strong>` não
    // é a sintaxe canônica do template e "gramática fechada" tem de recusar
    // o que não declarou.
    const m = /^<(\/?)([A-Za-z][\w-]*)((?:[^<>"']|"[^"]*"|'[^']*')*)>/.exec(
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

    const [bruto, barra, nomeBruto, attrs] = [m[0], m[1], m[2], m[3] || ""];
    const nome = nomeBruto.toLowerCase();
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
      // `</span onclick="...">` é fechamento com atributo: o browser ignora,
      // mas a gramática não pode aprovar o que não sabe ler.
      if (attrs.trim()) {
        erros.push(`${onde}: fechamento </${nome}> não aceita atributo`);
        return;
      }
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

      const chavesVistas = new Set();
      for (const [, chave, valorAttr] of encontrados) {
        if (chavesVistas.has(chave)) {
          // `class="ref" class="q"`: o browser fica com o primeiro, quem lê
          // o card fica com a impressão do segundo.
          erros.push(`${onde}: atributo '${chave}' repetido em <${nome}>`);
          return;
        }
        chavesVistas.add(chave);
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

      // Atributo declarado OBRIGATÓRIO: `<span>` cru não é markup do
      // gerador, é tag solta que ninguém pediu.
      for (const exigido of regra.exige || []) {
        if (!chavesVistas.has(exigido)) {
          erros.push(`${onde}: <${nome}> exige o atributo '${exigido}'`);
          return;
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

// ── Tipos ────────────────────────────────────────────────────────────────
// O validador certificava artefato que NÃO ABRE: `badges: "abc"` passava e
// quebrava no `.map` do template, interrompendo o render ANTES do aviso
// visual — ou seja, sem card e sem alarme (Codex, r10).

function exigirLista(valor, campo, onde, erros, obrigatorio) {
  if (valor === undefined || valor === null) {
    if (obrigatorio) erros.push(`${onde}: '${campo}' é obrigatório`);
    return [];
  }
  if (!Array.isArray(valor)) {
    erros.push(
      `${onde}: '${campo}' não é lista — o template chama .map() e o render ` +
        `MORRE antes de desenhar qualquer card`,
    );
    return [];
  }
  if (obrigatorio && valor.length === 0) {
    // Card sem nenhuma ação/opção existe na tela e não decide nada: o
    // usuário não tem o que despachar.
    erros.push(`${onde}: '${campo}' está vazio — o card não oferece decisão`);
  }
  return valor;
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
    validarTexto(s.title, "title", onde, erros, true);
    validarNumeroDeSecao(s.num, onde, erros);
    validarTexto(s.sub, "sub", onde, erros, false);
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
    for (const campo of CAMPOS_MARKUP) {
      validarMarkup(p[campo], campo, onde, erros, campo === "contexto");
    }
    validarBase64(p.conteudo_b64, onde, erros);

    // Tipos: sem isto o validador certificava artefato que NÃO ABRE.
    validarTexto(p.title, "title", onde, erros, true);
    const badges = exigirLista(p.badges, "badges", onde, erros, false);
    const acoes = exigirLista(p.actions, "actions", onde, erros, p.type === "despacho");
    const opcoes = exigirLista(p.options, "options", onde, erros, p.type === "escolha");

    for (const b of badges) {
      if (!b || typeof b !== "object" || Array.isArray(b)) {
        erros.push(`${onde}: entrada de badges não é objeto`);
        continue;
      }
      validarTexto(b.label, "badges[].label", onde, erros, true);
      validarTone(b.tone, `${onde} badge`, erros);
    }

    const chaves = new Set();
    for (const a of acoes) {
      if (!a || typeof a.key !== "string") {
        erros.push(`${onde}: ação sem key`);
        continue;
      }
      if (chaves.has(a.key)) erros.push(`${onde}: ação '${a.key}' repetida`);
      chaves.add(a.key);
      if (Array.isArray(a)) {
        erros.push(`${onde}: entrada de actions é lista, não objeto`);
        continue;
      }
      for (const campo of CAMPOS_ATRIBUTO.action) validarAtributo(a[campo], campo, onde, erros);
      validarTone(a.tone, `${onde} ação ${a.key}`, erros);
      validarTexto(a.label, `actions[${a.key}].label`, onde, erros, true);
      validarTexto(a.requires, `actions[${a.key}].requires`, onde, erros, false);
    }

    const vistasOpcoes = new Set();
    for (const o of opcoes) {
      if (!o || typeof o.key !== "string") {
        erros.push(`${onde}: opção sem key`);
        continue;
      }
      if (vistasOpcoes.has(o.key)) erros.push(`${onde}: opção '${o.key}' repetida`);
      vistasOpcoes.add(o.key);
      if (Array.isArray(o)) {
        erros.push(`${onde}: entrada de options é lista, não objeto`);
        continue;
      }
      for (const campo of CAMPOS_ATRIBUTO.option) validarAtributo(o[campo], campo, onde, erros);
      validarTexto(o.label, `options[${o.key}].label`, onde, erros, true);
      validarTexto(o.desc, `options[${o.key}].desc`, onde, erros, true);
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
// espaço, `#` ou acento — o processo saía 0 SEM VALIDAR NADA. E resolver só
// com `resolve()` não basta: no macOS `/tmp` e `/var` são symlink, e
// `import.meta.url` já vem com o link resolvido enquanto `argv[1]` não. Sem
// `realpathSync` dos dois lados, o validador morre em silêncio em qualquer
// pasta temporária do sistema.
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
