#!/usr/bin/env bash
# Sandbox local do conserto do espelho (#159). Simula o "push do mirror" contra
# um repo git local (o "público"), rodando os cenários que Gemini flash+pro
# exigiram, e prova: história LINEAR (sem force) + git pull FAST-FORWARD.
set -euo pipefail

ROOT="$(mktemp -d)"
REMOTE="$ROOT/public.git"     # o "tharso/prumo" público (bare)
STAGE="$ROOT/stage"           # o subset staged (o que o workflow monta)
CLIENT="$ROOT/client"         # um usuário que clonou (simula o Cowork)
PASS=0; FAIL=0
ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

git init -q --bare "$REMOTE"           # público começa VAZIO (testa 1a execução)
export GIT_AUTHOR_NAME=Bot GIT_AUTHOR_EMAIL=bot@x GIT_COMMITTER_NAME=Bot GIT_COMMITTER_EMAIL=bot@x

# ---- A função que vai pro workflow (lógica pura, testável) ----
mirror_push() {
  local remote="$1" stage="$2" sha="$3"
  local work; work="$(mktemp -d)/m"
  # 1) update se o público tem história; init se estiver vazio (fallback — achado do Pro)
  if git clone -q --depth 1 "$remote" "$work" 2>/dev/null && git -C "$work" rev-parse HEAD >/dev/null 2>&1; then
    :
  else
    rm -rf "$work"; mkdir -p "$work"
    git -C "$work" init -q -b main
    git -C "$work" remote add origin "$remote"
  fi
  # 2) troca o conteúdo preservando .git (find, não rsync — achado flash+pro)
  find "$work" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  cp -a "$stage"/. "$work"/
  git -C "$work" add -A
  # 3) commit SÓ se mudou (guard anti-commit-vazio — achado flash)
  if git -C "$work" rev-parse HEAD >/dev/null 2>&1 && git -C "$work" diff --cached --quiet; then
    echo "    (sem mudança no subset — nada a espelhar)"
    rm -rf "$work"; return 0
  fi
  git -C "$work" commit -q -m "mirror: sync from prumo-dev@${sha}"
  git -C "$work" push -q origin HEAD:main    # sem --force
  rm -rf "$work"
}
mirror_tag() {  # tag imutável, sem --force (achado flash+pro)
  local remote="$1" stage="$2" sha="$3" tag="$4"
  local work; work="$(mktemp -d)/mt"
  git clone -q --depth 1 "$remote" "$work"
  find "$work" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  cp -a "$stage"/. "$work"/
  git -C "$work" add -A
  git -C "$work" rev-parse HEAD >/dev/null 2>&1 && git -C "$work" diff --cached --quiet || git -C "$work" commit -q -m "release ${tag}"
  git -C "$work" push -q origin HEAD:main
  git -C "$work" tag -a "$tag" -m "Release ${tag}"
  git -C "$work" push -q origin "$tag"       # sem --force
  rm -rf "$work"
}
head_sha(){ git --git-dir="$REMOTE" rev-parse main; }
count(){ git --git-dir="$REMOTE" rev-list --count main; }

echo "== Cenário 1: público vazio (primeira execução) =="
mkdir -p "$STAGE"; printf 'v1\n' > "$STAGE/VERSION"; echo "# Prumo" > "$STAGE/README.md"; mkdir -p "$STAGE/skills/fim"; echo "fim" > "$STAGE/skills/fim/SKILL.md"
mirror_push "$REMOTE" "$STAGE" aaaaaaa
[ "$(count)" = "1" ] && ok "1 commit no público" || bad "esperava 1 commit, tem $(count)"
git clone -q "$REMOTE" "$CLIENT"
[ -f "$CLIENT/skills/fim/SKILL.md" ] && ok "cliente clonou com as skills" || bad "cliente sem skills"
C1=$(head_sha)

echo "== Cenário 2: update incremental → cliente faz git pull =="
printf 'v2\n' > "$STAGE/VERSION"; echo "novo" > "$STAGE/skills/fim/EXTRA.md"
mirror_push "$REMOTE" "$STAGE" bbbbbbb
[ "$(count)" = "2" ] && ok "2 commits (linear)" || bad "esperava 2, tem $(count)"
# o teste decisivo: o pull do cliente é FAST-FORWARD?
PULL=$(git -C "$CLIENT" pull --ff-only origin main 2>&1) && ok "git pull --ff-only funcionou (sem divergência)" || bad "pull divergiu: $PULL"
[ "$(cat "$CLIENT/VERSION")" = "v2" ] && ok "cliente recebeu v2" || bad "cliente não atualizou"
# ancestralidade real: C1 é ancestral do HEAD atual?
git --git-dir="$REMOTE" merge-base --is-ancestor "$C1" "$(head_sha)" && ok "história preservada (C1 é ancestral)" || bad "história reescrita — C1 não é ancestral"

echo "== Cenário 3: deleção de arquivo sai do subset =="
rm "$STAGE/skills/fim/EXTRA.md"
mirror_push "$REMOTE" "$STAGE" ccccccc
[ "$(count)" = "3" ] && ok "3 commits" || bad "esperava 3, tem $(count)"
git -C "$CLIENT" pull -q --ff-only origin main
[ ! -f "$CLIENT/skills/fim/EXTRA.md" ] && ok "arquivo removido no cliente" || bad "arquivo deletado ainda presente"

echo "== Cenário 4: run sem mudança no subset (guard anti-commit-vazio) =="
mirror_push "$REMOTE" "$STAGE" ddddddd
[ "$(count)" = "3" ] && ok "nenhum commit vazio criado (segue 3)" || bad "criou commit vazio! tem $(count)"

echo "== Cenário 5: push de tag (imutável, sem force) =="
printf 'v3\n' > "$STAGE/VERSION"
mirror_tag "$REMOTE" "$STAGE" eeeeeee v5.29.0
git --git-dir="$REMOTE" rev-parse v5.29.0 >/dev/null 2>&1 && ok "tag v5.29.0 criada no público" || bad "tag não criada"
git -C "$CLIENT" pull -q --ff-only origin main && ok "cliente ainda faz fast-forward após a tag" || bad "tag quebrou o fast-forward do cliente"

echo ""
echo "RESULTADO: $PASS ok, $FAIL falhas"
rm -rf "$ROOT"
[ "$FAIL" = "0" ]
