# First EC2 deployment: Ledger 201

This is a manual runbook for Aaron. It provisions no AWS resources automatically.
Use a single Ubuntu 24.04 LTS x86_64 EC2 instance. Run the Linux commands below
on that instance as the Ubuntu SSH administrator unless a command says otherwise.
Replace repository, branch/revision, key, model, IP, and domain placeholders.
Stop at any failed command; do not continue installing a partially built release.

## Decisions and preflight

- Python **3.13.14**, matching the tested local virtualenv, is pinned in
  `../.python-version`. Install it independently of Ubuntu's system Python using
  uv's managed Python. Do not replace `/usr/bin/python3`.
- Node **24.x** for builds (`frontend/.nvmrc`); local verification uses 24.18.0.
  This replaces the older 20.19.0 `.nvmrc` with the major actually tested locally.
  Install through nvm, not Ubuntu's default Node package. Node is not a runtime
  service. [Vite's Node requirements](https://vite.dev/guide/) are satisfied.
- One Uvicorn worker, no reload, listening on `127.0.0.1:8000` behind Nginx.
- `/opt/ledger201`: checkout and virtualenv, owned by `ledger:ledger`.
- `/var/lib/ledger201`: persistent SQLite data, owned by `ledger:ledger`, mode 750.
- `/etc/ledger201`: root-owned configuration directory, group `ledger`, mode 750;
  environment file mode 640. Nginx cannot read this file or the database.
- `/var/www/ledger201`: root-owned static build, directories 755/files 644.
  Copy only `frontend/dist/` here. This gives Nginx read access without exposing
  the checkout, virtualenv, source files, or backend secrets.

Before launch, choose the AWS account/region, instance size/storage budget, SSH
key, repository access method, release revision, and eventual domain. An x86_64
instance with at least 2 GiB RAM is a starting estimate for on-host builds, not a
capacity guarantee; monitor build memory and CPU credits. Use encrypted EBS and
retain backups independently of the instance. SQLite persistence across deploys
is not protection against volume deletion or instance loss.

These changes must first be reviewed and made available in your deployment
repository/release by Aaron. This preparation task does not commit or push.
The old root `ledger201.db` is removed from Git tracking while retained locally;
ignore rules do not erase historical commits. Do not deploy or copy that database.
No tracked environment or private-key files were found during preparation; this
is not a full historical secret audit.

**Access warning:** there is no application authentication. Anyone who can reach
the URL can access exposed financial APIs and potentially trigger paid AI calls.
An obscure URL, CORS, and HTTPS do not provide authentication. Aaron may choose
to accept public reachability for the immediate controlled Jacob test; make that
decision before importing real data or sharing the URL. Authentication is a
high-priority next production feature, not a long-term optional safeguard.

## 1. AWS console steps (manual)

1. Launch an Ubuntu 24.04 LTS x86_64 instance in a subnet with internet routing,
   an SSH key you control, and appropriate encrypted EBS storage.
2. Configure inbound Security Group rules:

   | Protocol/port | Source |
   | --- | --- |
   | TCP 22 (SSH) | Aaron's current public IPv4 address `/32` only |
   | TCP 80 (HTTP) | `0.0.0.0/0` |
   | TCP 443 (HTTPS) | `0.0.0.0/0` |

   Do not open 8000, database ports, Vite 5173, or other development ports. Update
   the SSH source when Aaron's home IP changes; never leave SSH open globally.
   These instructions use IPv4; do not add IPv6 ingress casually. Keep outbound
   access available for DNS, package installation, and backend OpenAI HTTPS calls.
   See [AWS security group guidance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules-reference.html).
3. Allocate and associate an Elastic IP before setting a domain. Ordinary public
   IPv4 addresses can change on stop/start. Elastic/public IPv4 addresses incur
   AWS charges; review costs in the console. See [EC2 addressing](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-instance-addressing.html).
4. SSH in as `ubuntu` using your private key stored outside this repository.

## 2. OS prerequisites and directories

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git curl ca-certificates build-essential python3 python3-venv nginx sqlite3 rsync snapd
# Reboot if the OS requests it, then reconnect before continuing.
sudo useradd --system --user-group --home-dir /var/lib/ledger201 --shell /usr/sbin/nologin ledger
sudo install -d -o ledger -g ledger -m 755 /opt/ledger201
sudo install -d -o ledger -g ledger -m 750 /var/lib/ledger201
sudo install -d -o root -g ledger -m 750 /etc/ledger201
sudo install -d -o root -g root -m 755 /var/www/ledger201
sudo install -d -o ledger -g ledger -m 700 /var/lib/ledger201/backups
```

Create the user once; on an existing installation inspect `id ledger` instead.
No login shell or sudo permission is given to the service account. The administrator
uses `sudo -u ledger ...` to run explicit maintenance commands.

## 3. Clone the release

```bash
sudo -u ledger git clone https://github.com/OWNER/REPOSITORY.git /opt/ledger201
sudo -u ledger git -C /opt/ledger201 switch YOUR_DEPLOYMENT_BRANCH
sudo -u ledger git -C /opt/ledger201 rev-parse HEAD
```

For a private repository, configure read-only repository access for this command
without embedding tokens in the URL or shell history. Keep deployment credentials
outside the checkout. Do not copy your workstation `.env`, virtualenv, or database.

## 4. Install the tested Python and backend dependencies

uv is used only to obtain the pinned Python and create a virtualenv; this does not
convert the project to a different dependency manager. Review its installer first.
See [uv installation](https://docs.astral.sh/uv/getting-started/installation/) and
[managed Python](https://docs.astral.sh/uv/guides/install-python/).

```bash
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/ledger-uv-install.sh
less /tmp/ledger-uv-install.sh
sudo env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh /tmp/ledger-uv-install.sh
sudo env UV_PYTHON_INSTALL_DIR=/opt/ledger201-python /usr/local/bin/uv python install 3.13.14
sudo -u ledger env UV_PYTHON_INSTALL_DIR=/opt/ledger201-python /usr/local/bin/uv venv --python 3.13.14 --seed /opt/ledger201/.venv
sudo -u ledger /opt/ledger201/.venv/bin/python --version
sudo -u ledger /opt/ledger201/.venv/bin/python -m pip install -r /opt/ledger201/backend/requirements.txt
sudo -u ledger /opt/ledger201/.venv/bin/python -m pip check
```

The managed interpreter lives outside `/home`, so systemd's `ProtectHome=true`
does not prevent the virtualenv from using it. Do not remove `/opt/ledger201-python`
while this virtualenv depends on it. If the pinned interpreter/dependencies cannot
be installed on Ubuntu, stop and resolve that before enabling the application;
the Windows test results are not an Ubuntu installation test.

## 5. Production environment and fresh schema

```bash
sudo install -o root -g ledger -m 640 /opt/ledger201/deploy/ledger201.env.example /etc/ledger201/ledger201.env
sudoedit /etc/ledger201/ledger201.env
```

Set the real backend-only key and the model already tested for Ledger:

```dotenv
DATABASE_URL=sqlite:////var/lib/ledger201/ledger201.db
OPENAI_API_KEY=replace-with-your-production-key
OPENAI_MODEL=replace-with-your-tested-model
```

Do not put secrets in `VITE_*` variables; those are compiled into public JavaScript.
The service's `EnvironmentFile` takes precedence over backend `.env` values.
Do not place a backend `.env` on EC2. No `FRONTEND_ORIGIN` is necessary: production
uses same-origin requests. Existing localhost/127.0.0.1 port-5173 CORS support
continues to serve development; CORS is not an access-control boundary.

Initialize using systemd's environment-file parser rather than sourcing secrets
as shell code:

```bash
sudo systemd-run --unit=ledger201-init --wait --collect --pipe \
  --uid=ledger --gid=ledger --working-directory=/opt/ledger201/backend \
  --property=EnvironmentFile=/etc/ledger201/ledger201.env --property=UMask=0027 \
  /opt/ledger201/.venv/bin/python -m app.init_db
sudo -u ledger sqlite3 /var/lib/ledger201/ledger201.db '.tables'
sudo -u ledger sqlite3 /var/lib/ledger201/ledger201.db 'SELECT COUNT(*) FROM orders; SELECT COUNT(*) FROM locations;'
```

Both counts should be zero for a fresh database. `app.init_db` and current app
startup use SQLAlchemy `create_all`: create missing tables, preserve existing
records, never drop/reset/seed. Startup retains this behavior for compatibility.
There is **no automatic demo seed**. Never run `app.demo.seed` with the production
environment; its explicit developer command uses the configured database by default.
For local demos, pass a separate `--database-url sqlite:///./demo-ledger201.db`.
Create the real location and import reports through the application after HTTPS
and the access decision; do not populate fake business records for initialization.

`create_all` is not a migration framework: it does not add/change columns in
existing tables. The existing `python -m app.migrate_provenance` is an explicit,
SQLite-only, idempotent development migration for an old orders table; it is not
needed for a fresh schema and must not be blindly run on every release. Before
any schema-changing production release, back up, review and test a specific
migration against a copy. Adopt Alembic before significant production schema
evolution. Never use `drop_all`, delete the DB, or reseed as an upgrade strategy.
Later PostgreSQL/RDS requires a driver, migrated schema/data, and testing; engine
creation already avoids SQLite-only arguments for other SQLAlchemy URLs.

## 6. Node and frontend build

Install nvm for the service account using its explicitly assigned data-directory
home; the runtime service does not need Node. See [nvm documentation](https://github.com/nvm-sh/nvm).

```bash
sudo -u ledger git clone --depth 1 --branch v0.40.8 https://github.com/nvm-sh/nvm.git /var/lib/ledger201/.nvm
sudo -u ledger -H bash <<'BUILD'
set -euo pipefail
export NVM_DIR=/var/lib/ledger201/.nvm
. "$NVM_DIR/nvm.sh"
cd /opt/ledger201/frontend
nvm install
nvm use
node --version
npm ci
npm test
VITE_API_BASE_URL=/api npm run build
npm run lint
BUILD
sudo rsync -a --chown=root:root --chmod=D755,F644 /opt/ledger201/frontend/dist/ /var/www/ledger201/
```

`npm run build` produces `frontend/dist`. Production defaults to `/api`, and the
build command makes this explicit to avoid a stray `.env.production` override.
Development without an override still uses `http://127.0.0.1:8000`. Existing API
paths already start with `/api`; the client prevents `/api/api/...`. Explicit
`VITE_API_BASE_URL` origins or API bases continue to work and require a rebuild.
Never use `vite`, `vite preview`, or `--reload` as production processes.

## 7. Install the service and Nginx site

```bash
sudo install -m 644 /opt/ledger201/deploy/ledger201.service.example /etc/systemd/system/ledger201.service
sudo systemd-analyze verify /etc/systemd/system/ledger201.service
sudo systemctl daemon-reload
sudo systemctl enable --now ledger201
curl --fail http://127.0.0.1:8000/health

sudo install -m 644 /opt/ledger201/deploy/nginx-ledger201.conf.example /etc/nginx/sites-available/ledger201
sudoedit /etc/nginx/sites-available/ledger201
# Set server_name to your domain; the placeholder also works for a temporary
# IP-based smoke test when this is the only enabled site. Do not obtain TLS yet.
sudo ln -s /etc/nginx/sites-available/ledger201 /etc/nginx/sites-enabled/ledger201
sudo unlink /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
curl --fail http://localhost/health
curl --fail http://localhost/
sudo ss -ltnp
```

The unlink command applies only to the stock default site on a fresh instance.
Do not remove other applications' sites. Port 8000 must show `127.0.0.1`, never
`0.0.0.0` or `::`. The service is non-root, uses one worker, restarts on failure,
logs to journald, and has a read-only filesystem except `/var/lib/ledger201` and
its private temporary directory. A missing/incorrect production DB URL will fail
instead of silently writing a database into the read-only checkout.

Nginx `proxy_pass` has **no trailing slash/URI**, preserving `/api/...` for FastAPI
([Nginx semantics](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass)).
`/health` is lightweight liveness, not database or OpenAI readiness. Proxy headers
are trusted only from loopback by Uvicorn. A 2 MiB request limit allows pasted
monthly reports; requests exceeding it return 413. The 300-second proxy read
timeout accommodates multi-round analyst calls but does not guarantee provider
availability. No backend secrets/configuration are returned by health.

Test direct SPA loads and refreshes in a browser at `/`, `/square-reports`,
`/vendor`, `/vendors`, `/location`, and `/daily-review`. The chatbot is `/`, not
`/chatbot`; `/vendors` is an alias for the existing `/vendor` route. Also verify:

```bash
curl --fail http://localhost/square-reports
curl --fail http://localhost/vendors
curl --fail http://localhost/api/locations
curl -i http://localhost/api/not-a-route
curl -i http://localhost/assets/missing.js
curl -i http://localhost/missing.css
```

SPA routes return index HTML. API locations returns JSON, missing API paths return
FastAPI JSON 404, and missing assets return 404 rather than index HTML. In browser
Network tools confirm requests hit `/api/...` on the same origin with no localhost
or doubled `/api`. These Linux/Nginx checks must run on the target; repository
unit tests do not simulate Nginx or systemd.

## 8. Domain and HTTPS

Once HTTP works, point the real domain's DNS A record to the Elastic IP, replace
`ledger.example.com` in the enabled Nginx site, and verify DNS resolves correctly.
Do not publish an AAAA record unless IPv6 is configured end to end. Obtain TLS
with Certbot only after the actual domain is reachable on port 80:

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo snap install --classic certbot
sudo /snap/bin/certbot --nginx -d YOUR_REAL_DOMAIN --redirect
sudo /snap/bin/certbot renew --dry-run
curl --fail https://YOUR_REAL_DOMAIN/health
curl -I http://YOUR_REAL_DOMAIN/
```

Follow [Certbot's Nginx instructions](https://certbot.eff.org/instructions?ws=nginx&os=snap).
Confirm HTTP redirects to HTTPS and certificate renewal works before Jacob uses
real data. No fake certificates or repository certificate files. Certbot edits
the installed Nginx configuration; do not overwrite it with the HTTP-only template
on later deploys. HTTPS encrypts traffic but does not authenticate users.

## 9. Diagnostics

```bash
sudo systemctl status ledger201
sudo journalctl -u ledger201 -f
sudo journalctl -u ledger201 --since '1 hour ago'
sudo nginx -t
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
df -h /var/lib/ledger201
```

Python is unbuffered; Uvicorn/application logs go to systemd/journald. Do not enable
debug logging of request bodies, API keys, or full provider responses. A 502 usually
requires checking service status/logs and loopback health; 413 means the Nginx
body-size limit was exceeded. Do not expose the backend port to debug either issue.

## 10. Backups and safe updates

Use SQLite's online backup command instead of copying a live DB file. Store an
additional encrypted copy off-instance using your approved backup process and
practice restoration; backups in `/var/lib` alone share the instance's failure risk.

```bash
backup_file="/var/lib/ledger201/backups/ledger201-$(date -u +%Y%m%dT%H%M%SZ).db"
sudo -u ledger sqlite3 /var/lib/ledger201/ledger201.db ".backup '$backup_file'"
sudo -u ledger sqlite3 "$backup_file" 'PRAGMA integrity_check;'
sudo -u ledger git -C /opt/ledger201 status --short
sudo -u ledger git -C /opt/ledger201 rev-parse HEAD
# Save this old revision in the release log before updating.
sudo -u ledger git -C /opt/ledger201 fetch origin
# Inspect the release diff, especially requirements and schema changes.
sudo systemctl stop ledger201
sudo -u ledger git -C /opt/ledger201 pull --ff-only
sudo -u ledger /opt/ledger201/.venv/bin/python -m pip install -r /opt/ledger201/backend/requirements.txt
sudo -u ledger /opt/ledger201/.venv/bin/python -m pip check
```

Expect a maintenance window while the service is stopped. If dependencies changed,
validate them before restart. Run the frontend build/test block in section 6 again
(`nvm use`, `npm ci`, `npm test`, build, lint). Stop on failure. No schema changes
are needed for this deployment-preparation release. For a later schema change,
run its reviewed, backup-tested migration with the same EnvironmentFile mechanism
as initialization; do not assume `create_all` migrates old tables.

```bash
# Publish assets only after the build and checks succeed. Keep older hashed
# assets temporarily so browsers with the prior index can still finish loading.
sudo rsync -a --exclude=index.html --chown=root:root --chmod=D755,F644 /opt/ledger201/frontend/dist/ /var/www/ledger201/
sudo install -o root -g root -m 644 /opt/ledger201/frontend/dist/index.html /var/www/ledger201/index.html.next
sudo mv /var/www/ledger201/index.html.next /var/www/ledger201/index.html
sudo systemctl restart ledger201
curl --fail http://127.0.0.1:8000/health
curl --fail https://YOUR_REAL_DOMAIN/health
curl --fail https://YOUR_REAL_DOMAIN/api/locations
```

Nginx needs reload only when its configuration changes (`nginx -t` first).
If the service unit changes, reinstall it and run `systemctl daemon-reload` before
restart. Do not overwrite the environment file, copy any database, run demo seed,
or delete `/var/lib/ledger201` during deployment. Git updates affect only the
checkout, so production data persists independently.

## 11. Rollback

For a code-only release whose schema is compatible, stop the service, check out
the saved good commit, reinstall its requirements, rebuild/publish its frontend
using the same commands, and restart/check health. No database paths are touched:

```bash
sudo systemctl stop ledger201
sudo -u ledger git -C /opt/ledger201 checkout --detach SAVED_GOOD_COMMIT
# Repeat dependency install, build/publish, restart and health checks above.
```

Switch back to the deployment branch before a future `git pull`. Alternatively,
Aaron can prepare a reviewed revert release upstream. If schema changes occurred,
first establish compatibility; a code checkout does not roll back a database.
Restoring a backup is a separate, deliberate maintenance operation that can lose
newer records. Never automatically restore, reset, or delete production data as
part of application rollback.

## Preparation verification (October 6, 2026)

- Backend: 219 tests passed, including six deployment cases for URL override,
  local fallback, cross-thread SQLite access, non-SQLite engine options, health,
  and fresh/repeated startup and schema initialization without demo records.
- Existing analyst and provenance tests pass; no live OpenAI calls were made.
- `python -m compileall app` and `python -m pip check`: passed.
- Frontend: 31 tests passed, including three API URL cases; build and lint passed.
- Build output is `frontend/dist`; Vite reports a non-failing >500 kB bundle warning.
- `git diff --check`: passed. Database untracking is staged; application/docs
  changes are uncommitted. The local root database file remains intact.
- Verification environment: Windows, Python 3.13.14, Node 24.18.0. No AWS launch,
  Ubuntu package installation, systemd execution, Nginx execution, DNS change,
  certificate issuance, or live browser test through Nginx was performed.

No failing local check blocks preparation. Before serving Jacob, Aaron must make
the reviewed revision available to EC2, supply repository access/key/model/domain,
explicitly decide on the unauthenticated test exposure, and complete the target
Ubuntu install, `systemd-analyze verify`, `nginx -t`, API/SPA smoke tests, and TLS
steps above. Do not interpret local unit tests as proof those target checks passed.
