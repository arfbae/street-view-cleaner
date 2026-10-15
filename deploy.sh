#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="street-view-cleaner"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"
DOWN=0
LOGS=0
NO_BUILD=0

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [--down] [--logs] [--no-build] [--timeout SECONDS]

  --down              Stop and remove the Compose stack.
  --logs              Follow application logs after startup.
  --no-build          Start without rebuilding the image.
  --timeout SECONDS  Health-check timeout (default: 120).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --down) DOWN=1; shift ;;
    --logs) LOGS=1; shift ;;
    --no-build) NO_BUILD=1; shift ;;
    --timeout) TIMEOUT_SECONDS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

command -v docker >/dev/null 2>&1 || { echo "Docker is required." >&2; exit 1; }

if (( DOWN )); then
  docker compose down
  exit 0
fi

if [[ ! -f .env ]]; then
  [[ -f .env.template ]] || { echo "Run this script from the project root." >&2; exit 1; }
  cp .env.template .env
  echo "Created .env from .env.template; add live provider credentials before processing."
fi

compose_args=(up -d)
(( NO_BUILD )) || compose_args+=(--build)
docker compose "${compose_args[@]}"

deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
ready=0
while (( $(date +%s) < deadline )); do
  if docker compose exec -T "$SERVICE" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done

if (( ! ready )); then
  docker compose ps
  docker compose logs --tail 100 "$SERVICE"
  echo "Application did not become healthy within ${TIMEOUT_SECONDS}s." >&2
  exit 1
fi

docker compose ps
echo "Street View Cleaner is ready at http://localhost:8000"
echo "Use ./deploy.sh --logs to follow logs or ./deploy.sh --down to stop."

if (( LOGS )); then
  docker compose logs -f "$SERVICE"
fi
