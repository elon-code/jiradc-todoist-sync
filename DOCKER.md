# Run Jira⇄Todoist Sync in Docker

This guide shows how to run the sync as a background service using Docker.

## Quick start (recommended)

1) Copy the env template and edit values:

```bash
cp .env.example .env
# edit .env and set JIRA_API_TOKEN, TODOIST_API_TOKEN, JIRA_SERVER_URL
```

2) Start with Compose (detached):

```bash
docker compose up -d --build
```

3) Follow logs:

```bash
docker compose logs -f
```

4) Stop/Start:

```bash
docker compose stop
# or
docker compose restart
```

## Direct Docker (without Compose)

```bash
docker build -t jiradc-todoist-sync:latest .

docker run -d \
  --name jiradc-todoist-sync \
  --restart unless-stopped \
  -e JIRA_API_TOKEN="$JIRA_API_TOKEN" \
  -e TODOIST_API_TOKEN="$TODOIST_API_TOKEN" \
  -e JIRA_SERVER_URL="$JIRA_SERVER_URL" \
  -e SYNC_INTERVAL_MINUTES=5 \
  -e DEBUG=false \
  jiradc-todoist-sync:latest
```

View logs:

```bash
docker logs -f jiradc-todoist-sync
```

## Notes

- The container entrypoint validates required env vars and exits with an error if missing.
- The app writes no secrets to `config.json`. Never commit `.env`.
- For live-edit during development, `docker-compose.yml` mounts the repo at `/app`.
- In production, remove the volume mount and bake the code into the image only.

## Configuration mapping

- SYNC_INTERVAL_MINUTES -> `config["sync_interval_minutes"]`
- DEBUG=true -> sets higher log level via `main.py` (set `debug: true` in config.json or use env/compose to override)

## Update the image

```bash
docker compose pull  # if using a remote registry
# or rebuild locally
docker compose build --no-cache
```

## Troubleshooting

- Missing env error at startup: ensure `JIRA_API_TOKEN`, `TODOIST_API_TOKEN`, and `JIRA_SERVER_URL` are set.
- HTTP 401 from Jira: verify the Jira token and server URL.
- No tasks sync: turn on DEBUG and check logs for filters like `exclude_statuses`.
