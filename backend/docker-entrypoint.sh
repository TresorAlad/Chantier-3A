#!/bin/sh
set -e

cd /app

demo_args() {
  case "$(printf '%s' "${CHANTIER3A_DEMO:-}" | tr '[:upper:]' '[:lower:]')" in
    1 | true | yes | on) printf '%s' "--demo" ;;
    *) ;;
  esac
}

run_migrate() {
  if [ "${CHANTIER3A_SKIP_MIGRATE:-0}" = "1" ]; then
    return 0
  fi
  billetterie-api migrate
}

run_serve() {
  run_migrate
  demo="$(demo_args)"
  if [ -n "$demo" ]; then
    exec billetterie-api serve "$demo" "$@"
  fi
  exec billetterie-api serve "$@"
}

case "$1" in
  migrate)
    shift
    exec billetterie-api migrate "$@"
    ;;
  serve)
    shift
    run_serve "$@"
    ;;
  "")
    run_serve
    ;;
  *)
    exec billetterie-api "$@"
    ;;
esac
