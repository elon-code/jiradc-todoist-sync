#!/usr/bin/env bash
set -euo pipefail

# Colors
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

req_vars=("JIRA_API_TOKEN" "TODOIST_API_TOKEN" "JIRA_SERVER_URL")
missing=()

for v in "${req_vars[@]}"; do
  if [ -z "${!v-}" ]; then
    missing+=("$v")
  fi
done

if [ ${#missing[@]} -ne 0 ]; then
  echo -e "${RED}Missing required environment variables:${NC} ${missing[*]}" >&2
  echo -e "${YELLOW}Set them via docker run -e or docker compose .env file.${NC}" >&2
  exit 1
fi

export PYTHONUNBUFFERED=1

echo -e "${GREEN}Starting Jira⇄Todoist sync service...${NC}"
exec python -u /app/main.py "$@"
