# Portainer Self-Contained Staging Deployment

This guide deploys Cyclope Central to an Ubuntu VPS through a Portainer stack without requiring a separate `.env` file. It uses the existing Phase 3 production-ready services, RustDesk OSS services, and Caddy for automatic HTTPS.

- Domain: `carlislestudentscte.cloud`
- Primary URL: `https://central.carlislestudentscte.cloud`
- Default Portainer Git Compose path: `docker-compose.yml`
- Alternate copy for manual/web-editor workflows: `deployment/portainer/docker-compose.staging.selfcontained.yml`

This staging workflow does not add product features, arbitrary scripting, PowerShell execution from the server, remote shell, credential vaulting, or custom remote desktop.

## DNS prerequisites

Create an `A` record before deploying:

| Host | Type | Value |
| --- | --- | --- |
| `central.carlislestudentscte.cloud` | `A` | Public IPv4 address of the Ubuntu VPS |

If the VPS also has IPv6, add an `AAAA` record only after confirming IPv6 firewall and routing work correctly.

## Firewall ports

Open these inbound ports on the VPS and any cloud firewall/security group:

| Port | Protocol | Purpose |
| --- | --- | --- |
| `80` | TCP | Caddy HTTP-01 challenge and redirect support |
| `443` | TCP | Caddy HTTPS for dashboard and API |
| `21115` | TCP | RustDesk hbbs NAT/type test |
| `21116` | TCP | RustDesk hbbs rendezvous |
| `21116` | UDP | RustDesk hbbs hole punching |
| `21117` | TCP | RustDesk hbbr relay |
| `21118` | TCP | RustDesk web client/support channel |
| `21119` | TCP | RustDesk web client/support channel |

Do not route RustDesk TCP/UDP through Caddy; Caddy only proxies HTTP(S) dashboard/API traffic.

## Portainer stack deployment

For Portainer Git deployment, use:

- Repository URL: `git@github.com:wagnerks1990/cyclope-central.git`
- Repository reference: `refs/heads/main`
- Compose path: `docker-compose.yml`

The root `docker-compose.yml` is intentionally a staging/Portainer self-contained stack with root-relative build contexts. The existing `deployment/portainer/docker-compose.staging.selfcontained.yml` remains available for manual web-editor paste workflows or environments that prefer keeping deployment files under `deployment/`.

1. In Portainer, open **Stacks** and select **Add stack**.
2. Name the stack `cyclope-central-staging`.
3. Choose **Git repository** for the default path above, or choose **Web editor** and paste the full contents of `deployment/portainer/docker-compose.staging.selfcontained.yml`.
4. Review the `backend` and `frontend` build contexts. If Portainer cannot build from your Git repository in your environment, replace the build sections with image names from your private registry.
5. Deploy the stack.
6. Watch the backend logs until migrations complete and Uvicorn starts.
7. Visit `https://central.carlislestudentscte.cloud` and complete first-run setup.

## Included services

The self-contained stack includes:

- `frontend`
- `backend`
- `postgres`
- `redis`
- `rustdesk-hbbs`
- `rustdesk-hbbr`
- `caddy`

Named volumes are used for durable staging data:

- `postgres-data`
- `redis-data`
- `rustdesk-data`
- `backend-secrets`
- `caddy-data`
- `caddy-config`

Back up these named volumes before destructive Portainer operations.

## Automatic staging secrets

The backend startup command checks `CYCLOPE_JWT_SECRET_KEY` and `CYCLOPE_TOKEN_HASH_PEPPER`.

- If an explicit environment value is present, the backend uses it.
- If no value is present, the backend generates a strong random value.
- Generated values are stored in the `backend-secrets` named volume.
- Secret values are not printed to logs.
- The same generated secrets are reused on later container restarts because the named volume persists.

The staging Compose file intentionally uses generated secrets instead of committed secret values. PostgreSQL uses the documented staging default credentials from the Compose file; change them before treating the deployment as anything beyond staging.

## Overriding secrets later

To override generated staging secrets:

1. Stop the stack during a maintenance window.
2. Edit the Portainer stack.
3. Set explicit values for `CYCLOPE_JWT_SECRET_KEY` and `CYCLOPE_TOKEN_HASH_PEPPER` in the `backend.environment` section.
4. Redeploy the stack.
5. Log in again because changing the JWT secret invalidates existing access tokens.

Do not paste secrets into tickets, chat, documentation articles, or screenshots.

## Rotating secrets later

For staging rotation:

1. Announce a maintenance window.
2. Revoke active sessions where practical.
3. Set new explicit values for `CYCLOPE_JWT_SECRET_KEY` and/or `CYCLOPE_TOKEN_HASH_PEPPER`.
4. Redeploy the stack.
5. Re-enroll endpoint agents if token pepper rotation invalidates stored device secret hashes.
6. Confirm `/api/health`, login, and agent check-ins.

For production, keep secret rotation in a password manager or external secret system rather than relying on generated staging volume files.

## First-run setup

After the stack is healthy:

1. Open `https://central.carlislestudentscte.cloud`.
2. If setup is required, the frontend redirects to first-run setup.
3. Create the first organization and owner user with a strong password.
4. Save recovery details in your MSP operational documentation without storing passwords in Cyclope Central.

## Health checks

Useful checks from a workstation:

```bash
curl -fsS https://central.carlislestudentscte.cloud/api/health
curl -fsS https://central.carlislestudentscte.cloud/api/bootstrap/status
```

In Portainer, confirm these containers are healthy or running:

- `postgres`
- `redis`
- `backend`
- `frontend`
- `caddy`
- `rustdesk-hbbs`
- `rustdesk-hbbr`

## RustDesk verification

1. Confirm ports `21115/tcp`, `21116/tcp`, `21116/udp`, `21117/tcp`, `21118/tcp`, and `21119/tcp` are reachable from the networks where agents/users will connect.
2. Configure RustDesk clients with:
   - ID server: `central.carlislestudentscte.cloud`
   - Relay server: `central.carlislestudentscte.cloud`
   - Public key: use the key generated by RustDesk server if required by your client workflow.
3. Verify the Cyclope agent reports RustDesk status on the next authenticated check-in.

RustDesk remains the remote desktop provider. Cyclope Central does not implement custom remote desktop, screen capture, keylogging, arbitrary command execution, or server-driven PowerShell.

## Agent enrollment smoke test

1. Log in as an owner/admin.
2. Create a limited-use enrollment token using the backend API or helper script in a trusted administrative environment.
3. On a test endpoint, enroll the agent against `https://central.carlislestudentscte.cloud/api`.
4. Run a check-in and verify the device appears in the dashboard.
5. Confirm no secrets are printed in endpoint or backend logs.

## Backup notes

At minimum, back up these named volumes:

- `postgres-data` for the application database
- `redis-data` for Redis persistence
- `rustdesk-data` for RustDesk server data/keys
- `backend-secrets` for generated staging secrets
- `caddy-data` and `caddy-config` for ACME account/certificate state

Automated restore is intentionally not implemented. Practice manual database and volume restore procedures on a separate staging VPS before relying on backups.
