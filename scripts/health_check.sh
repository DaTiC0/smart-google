#!/usr/bin/env bash
set -euo pipefail

url="${1:-${HEALTH_URL:-http://127.0.0.1:5000/health}}"

response="$(curl -sS -m 10 -w $'\n%{http_code}' "$url")" || {
  echo "Health check failed: could not reach $url"
  exit 2
}

http_code="$(printf '%s\n' "$response" | tail -n 1)"
body="$(printf '%s\n' "$response" | sed '$d')"

printf '%s\n' "$body"

if [[ "$http_code" == "200" ]]; then
  echo "Health check passed ($http_code)"
  exit 0
fi

echo "Health check failed ($http_code)"
exit 1
