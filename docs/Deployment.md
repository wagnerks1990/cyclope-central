# Deployment

Cyclope Central is designed for self-hosted deployment with explicit first-run setup.

## Required production environment

Set these values before starting the backend in production:

- `CYCLOPE_ENVIRONMENT=production`
- `CYCLOPE_DATABASE_URL` pointing at PostgreSQL
- `CYCLOPE_REDIS_URL` pointing at Redis
- `CYCLOPE_JWT_SECRET` with at least 32 random characters
- `CYCLOPE_TOKEN_HASH_PEPPER` with at least 32 random characters
- `CYCLOPE_CORS_ALLOWED_ORIGINS` with the dashboard origin
- `NEXT_PUBLIC_API_BASE_URL` for the frontend

Do not use values from `.env.example` or `.env.production.example` without replacing placeholders. Production startup rejects placeholder/default JWT and token-pepper values without printing secret contents.

## Database migrations

Local:

```bash
./scripts/run-migrations.sh
```

Production:

```bash
cd backend
CYCLOPE_ENVIRONMENT=production alembic upgrade head
```

## First owner setup

Interactive dashboard setup is available at `/setup` while no owner user exists. For headless deployments, run:

```bash
./scripts/create-owner-user.py --organization "Example MSP" --email owner@example.com
```

The CLI prompts for the password and never prints passwords or tokens.

## Docker Compose workflow

```bash
cp .env.example .env
# edit .env and replace placeholders
./scripts/dev-up.sh
./scripts/run-migrations.sh
```

Use `./scripts/dev-down.sh` to stop local services. Remote access, arbitrary scripting, remote shell, and remote desktop remain out of scope.

## Production readiness phase 3

Use `docker-compose.production.yml` for production-style startup ordering, health checks, named volumes, and restart policies. Put all secrets in an environment file that is not committed. The production settings validator rejects placeholder JWT/token secrets.

Reverse proxy examples live in `infrastructure/reverse-proxy/`. Terminate HTTPS at the proxy and forward `/api/` to the backend and all other dashboard traffic to the frontend. RustDesk ports require raw TCP/UDP forwarding and should not be placed behind an HTTP-only proxy.

Supported deployment targets are Docker Compose on a Linux VM, Unraid Docker, Proxmox LXC/VM, or an equivalent self-hosted Linux host. For backups, create database backup jobs and validate backup artifacts; automated restore is intentionally not implemented and restore steps should be rehearsed manually from documented database dumps.
