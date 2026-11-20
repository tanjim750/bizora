# Deploying `bizora.ink`

| Public hostname | Nginx upstream | Check |
| --- | --- | --- |
| `bizora.ink` | `http://127.0.0.1:18180` (Next.js) | `https://bizora.ink/login` |
| `api.bizora.ink` | `http://127.0.0.1:18181` (Gunicorn) | `https://api.bizora.ink/healthz` |

Next.js also uses the private Django upstream for `/api/backend/` so browser sessions stay on the frontend origin. PostgreSQL 16 with pgvector stays private. WhiteNoise serves Django admin assets after `collectstatic`.

## Application services

Clone `https://github.com/tanjim750/bizora.git` into `~/bizora` for the deployment account. Install Node.js 24 under `~/.local/opt/node24` for the frontend user unit. In `~/bizora/frontend`, run `npm ci` followed by `npm run build` with that Node.js on `PATH`. The build downloads fonts from Google Fonts.

For the `bizora` hosting account without system Docker access, install Python 3.12 and PostgreSQL 16 with pgvector under the service account. The PostgreSQL unit expects the binary at `~/.local/opt/postgresql-16/bin/postgres` and the cluster at `~/.local/state/bizora/postgresql`. Initialize PostgreSQL with local peer and host SCRAM authentication. Create a `bizora` database owned by an unprivileged `bizora_app` login and install `vector` in that database using the database administrator role before migrating.

Copy `deploy/backend.env.example` to `~/.config/bizora/backend.env`, set a stable random secret and the database password, and set the file to mode `600`. Create the `~/bizora/.venv` Python 3.12 virtual environment and install `requirements.txt` into it. Install the three unit files under `~/.config/systemd/user/` and reload the user manager. Start `bizora-postgresql.service` first and wait for `pg_isready` on `127.0.0.1:15432`. Run `manage.py migrate --noinput` and `manage.py collectstatic --noinput` from the virtual environment, loading the backend environment for both commands. Then enable and start all three units with `systemctl --user enable --now`. The administrator can enable `loginctl enable-linger bizora` for startup at boot without an SSH session.

On a host with Docker access, use `docker compose -f compose.production.yml` for the backend and PostgreSQL in place of their two user units. Save the environment template as `.env.production`, replace both secrets, and omit native `POSTGRES_HOST` and `POSTGRES_PORT` because Compose sets them. Start `db`, build `web`, run `docker compose -f compose.production.yml run --rm web python manage.py migrate --noinput`, then start `web`. The Compose database uses its bootstrap login for Django in this minimal setup. The Next.js unit is the same for both options.

## Public Nginx and TLS

On CloudPanel, a site administrator should create two reverse-proxy sites using the upstream addresses in the table, then install valid TLS certificates for both hostnames through CloudPanel. Configure the proxy to preserve the public `Host` header, send `X-Forwarded-Proto: https` for HTTPS traffic, and redirect public HTTP to HTTPS. Cloudflare should use **Full (strict)** after the origin certificates are active. [CloudPanel reverse proxy](https://www.cloudpanel.io/docs/v2/frontend-area/add-site/) [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/)

On a standalone Nginx host, `nginx/bizora.conf` is the HTTP configuration to install before issuing both certificates and enabling redirects. Validate changes with `nginx -t` before reloading. On CloudPanel, use its site and vhost controls to manage the Nginx configuration.

## Smoke checks

```bash
curl -fsS http://127.0.0.1:18181/healthz
curl -fsS http://127.0.0.1:18180/api/backend/frontend/session
curl -fsS https://api.bizora.ink/healthz
curl -fsS https://bizora.ink/api/backend/frontend/session
```

Create the first operator and an active `OWNER` membership for a real workspace. Check browser sign-in and sign-out after enabling TLS. The backend remains on the repository's Django 4.2 series, which is out of upstream security support. [Django support schedule](https://www.djangoproject.com/download/)
