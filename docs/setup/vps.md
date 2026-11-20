# Bizora on a fresh VPS

The repository provides a Docker development setup for Django and PostgreSQL and a separate Node.js build for the Next.js frontend. A private installation can rehearse both components today. Public deployment needs a production Django server, HTTPS routing, and a supported Django release.

## Server prerequisites

| Requirement | What Bizora uses |
| --- | --- |
| VPS | One Ubuntu 24.04 LTS host on amd64 or arm64. Install Git, curl, OpenSSL, CA certificates, [Docker Engine with Buildx and Compose](https://docs.docker.com/engine/install/ubuntu/), and [Node.js 24 LTS with npm](https://nodejs.org/en/download/archive/v24) for the frontend service account. |
| Backend runtime | The Dockerfile supplies Python 3.12. Compose supplies PostgreSQL 16 through `pgvector/pgvector:0.8.7-pg16`, which is published for both architectures. |
| Network | Allow outbound DNS and HTTPS to your Git host, Docker Hub, PyPI, npm, `fonts.googleapis.com` and `fonts.gstatic.com` during installation and builds. Allow outbound access to any configured integration providers at runtime. |
| Public access | For production, point your domain to the VPS and allow inbound TCP 80 and 443 for the HTTPS reverse proxy. Restrict SSH to your administration network and keep ports 3000, 8000 and 5432 private. |
| Persistent storage | Reserve space for Docker images, PostgreSQL data and backups, and the Next.js build. If `/docs` editing is enabled, preserve `frontend/src/data/` across releases and give the frontend service account write access to it. |

## Private installation rehearsal

Run from a clean checkout on the VPS. The commands assume your deployment account can run Docker and authenticate to GitHub for this repository. Create the environment file once and retain its values across restarts. `openssl rand -hex 32` can generate independent values for each secret.

```bash
git clone git@github.com:tanjim750/bizora.git
cd bizora
umask 077
cp .env.example .env
```

Edit the root `.env` to contain these settings. Replace both secret placeholders before continuing. Remove any active `DATABASE_URL` or `POSTGRES_SSLMODE` when using the bundled database. An active `DATABASE_URL` takes precedence over the Compose database host and credentials.

```dotenv
DEBUG=False
SECRET_KEY=REPLACE_WITH_RANDOM_SECRET
DJANGO_SETTINGS_MODULE=bizora.settings
ALLOWED_HOSTS=127.0.0.1,localhost,web
BIZORA_DATABASE=postgresql
POSTGRES_DB=bizora
POSTGRES_USER=bizora
POSTGRES_PASSWORD=REPLACE_WITH_RANDOM_PASSWORD
```

Build the image before starting services. The repository `.dockerignore` excludes environment files, local SQL dumps, dependencies and Git history. Keep the `.env` on the host for Compose runtime injection.

Start a loopback-only Django container using the existing Compose build and database definitions. `docker compose run` publishes only the explicit port mapping below. The initial migration creates `vector` and requires permission to install it. For managed PostgreSQL, have a database administrator enable the extension in the target database before migrating if the Django migration role lacks that permission.

```bash
docker compose config --quiet
docker compose up -d --wait db
docker compose build web
docker compose run -d --rm --name bizora-vps-rehearsal \
  --publish 127.0.0.1:8000:8000 web
docker logs -f bizora-vps-rehearsal
```

After the logs show that migrations finished and Django started, exit the log viewer with Ctrl+C. From a second shell in the repository root, confirm the database extension and Django route, then build and start Next.js.

```bash
docker compose exec -T db psql -U bizora -d bizora \
  -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
curl --fail --show-error http://127.0.0.1:8000/api/frontend/session/

cd frontend
cp .env.example .env.production.local
npm ci
npm test
npm run build
npm run start -- --hostname 127.0.0.1 --port 3000
```

`DJANGO_API_ORIGIN=http://127.0.0.1:8000` is the server-side address for this host-based frontend. Next.js needs access to Google Fonts during `npm run build`, then serves the downloaded assets itself. [Next.js font documentation](https://nextjs.org/docs/app/api-reference/components/font)

From another shell, check `curl -fsS http://127.0.0.1:3000/login -o /dev/null` and `curl -fsS http://127.0.0.1:3000/api/backend/frontend/session`. The session response should contain `"authenticated":false` and an empty `businesses` array. With `DEBUG=False`, Django marks its session and CSRF cookies `Secure`. Verify browser sign-in through the production HTTPS hostname. To stop the rehearsal, end Next.js with Ctrl+C, run `docker stop bizora-vps-rehearsal`, then run `docker compose stop db` from the repository root. The named PostgreSQL volume retains its data.

## Changes required for public deployment

1. **Upgrade Django.** `requirements.txt` pins the final Django 4.2 patch, `4.2.30`. Upstream support for Django 4.2 ended on April 7, 2026. A supported line such as Django 5.2 LTS needs a separate repository upgrade and PostgreSQL 16 verification. [Django support schedule](https://www.djangoproject.com/download/)
2. **Use production runtime settings.** The [domain deployment guide](../../deploy/README.md) covers Gunicorn, static files, loopback bindings, migrations and systemd. Run `python manage.py check --deploy` with the actual production settings. [Django deployment checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
3. **Run Next.js as a persistent service.** Build with `npm ci` and `npm run build`. Use systemd with `WorkingDirectory` set to the `frontend` checkout, an absolute path to the installed Node.js 24 executable, a restart policy, and a non-root account. Start with `node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000`. Keep `DJANGO_API_ORIGIN` set to the internal Django address.
4. **Route HTTPS through the reverse proxy.** Forward the public hostname and `X-Forwarded-Proto: https` to Next.js. Send `/api/backend/` and the regular site routes to Next.js, keeping the browser and session cookies on one origin. Handle public HTTP redirects and HSTS at the reverse proxy. Keep `127.0.0.1` in Django's `ALLOWED_HOSTS` for Next.js upstream calls. If Django's `/admin/` or `/ops/` are exposed, add the public hostname to `ALLOWED_HOSTS`, configure Django to trust the scheme header only from the controlled proxy, account for the public HTTPS origin in CSRF configuration, and set `STATIC_ROOT`, run `collectstatic`, and serve `/static/`. Avoid redirecting internal HTTP calls from Next.js to HTTPS on port 8000. [Django proxy settings](https://docs.djangoproject.com/en/4.2/ref/settings/#secure-proxy-ssl-header) [Next.js self-hosting guide](https://nextjs.org/docs/app/guides/self-hosting)
5. **Provision the first business workspace.** Create a Django login and a `Business` with an active `BusinessMembership` for that user. An initial business administrator needs an `OWNER` membership. `createsuperuser` grants Django administrative privileges but leaves the frontend workspace list empty until the membership is created. Set up database backups and verify that you can restore them.
6. **Decide which optional routes to expose.** Providers such as Dialyra and Steadfast need credentials and explicitly routed Django webhook URLs outside Next.js's `/api/backend/` path. If `/docs` is intended to remain private, enforce access on the content API before publishing it. The current `GET /api/docs/content` returns content without the `/docs` page's access check. Restrict both paths at the reverse proxy until that is addressed.

## Release checks

- Check HTTP redirects to HTTPS and only intended ports are reachable externally.
- Check `https://YOUR_DOMAIN/login` and `https://YOUR_DOMAIN/api/backend/frontend/session`. Sign in with a real workspace membership and confirm that the browser receives `Secure` session and CSRF cookies.
- Open a business workspace, perform an authorized test write and sign out. A working read-only session URL alone cannot validate proxy headers or CSRF handling for writes.
- If enabled, check Django admin CSS and forms, configured webhook delivery and documentation access. Restart the services and verify that they recover and retain their data.
