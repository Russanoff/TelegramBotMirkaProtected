#!/bin/bash
# Выкатка бота на сервер (по docs/RUNBOOK.md, раздел 4). Запуск с Мака из папки проекта:
#   bash tools/deploy.sh            - выкатить то, что сейчас в origin/main
#   bash tools/deploy.sh rollback   - вернуть сервер на предыдущий выкаченный коммит
# Шаги: проверка, что локальный main запушен; копия базы в /root/backups/; git pull --ff-only;
# компиляция всех .py; перезапуск bot.service, затем api.service (~30 с без подписок и вебхука ЮKassa);
# проверка, что сервисы active и в журнале нет ошибок. Если после выкатки сервис не поднялся - автоматический откат.
set -euo pipefail
cd "$(dirname "$0")/.."

HOST="root@31.56.48.61"
KEY="$HOME/.ssh/mirka_trial"
DIR="/root/TelegramBotMirkaProtected"
# через Wi-Fi в обход VPN: через туннель Happ SSH к серверу зависает
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -i "$KEY")
if ifconfig en1 2>/dev/null | grep -q "status: active"; then SSH+=(-o BindInterface=en1); fi
run() { "${SSH[@]}" "$HOST" "$@"; }

MODE="${1:-deploy}"

if [ "$MODE" = "deploy" ]; then
  git fetch -q origin main
  if [ "$(git rev-parse main)" != "$(git rev-parse origin/main)" ]; then
    echo "Локальный main не совпадает с origin/main: сначала git push (или git pull)."; exit 1
  fi
  TARGET="$(git rev-parse --short origin/main)"
  echo "Выкатываю $TARGET: $(git log -1 --format=%s origin/main)"
fi

run "MODE=$MODE DIR=$DIR bash -s" <<'REMOTE'
set -euo pipefail
cd "$DIR"
ts=$(date +%Y%m%d_%H%M%S)
prev_file=/root/backups/last_deployed_before.txt
check() {
  sleep 3
  for s in bot.service api.service; do
    st=$(systemctl is-active "$s" || true)
    echo "$s: $st"
    [ "$st" = "active" ] || return 1
  done
  return 0
}
restart() {
  systemctl restart bot.service; sleep 15
  systemctl restart api.service; sleep 25
}

if [ "$MODE" = "rollback" ]; then
  [ -f "$prev_file" ] || { echo "Нет записи о предыдущем коммите"; exit 1; }
  prev=$(cat "$prev_file"); echo "Откат на $prev"
  git checkout -q "$prev"; restart; check; git log --oneline -1
  echo "Сервер на коммите $prev (detached). Вернуться на main: git checkout main на сервере или bash tools/deploy.sh."
  exit 0
fi

mkdir -p /root/backups
venv/bin/python -c "import sqlite3,sys; s=sqlite3.connect('database.db'); d=sqlite3.connect(sys.argv[1]); s.backup(d); d.close()" "/root/backups/database_$ts.db"
chmod 600 "/root/backups/database_$ts.db"; echo "Копия базы: /root/backups/database_$ts.db"

before=$(git rev-parse --short HEAD); echo "$before" > "$prev_file"
git checkout -q main
git pull -q --ff-only
after=$(git rev-parse --short HEAD)
echo "Код: $before -> $after"
venv/bin/python -m py_compile $(git ls-files '*.py') && echo "Компиляция: ok"
restart
if ! check; then
  echo "!!! Сервис не поднялся - откатываю на $before"
  journalctl -u bot.service -u api.service --since "-2min" --no-pager | tail -20
  git checkout -q "$before"; restart; check || true
  exit 1
fi
systemctl is-active nginx
echo "Предупреждения и ошибки за 2 минуты:"
journalctl -u bot.service -u api.service --since "-2min" -p warning --no-pager | tail -10
REMOTE
