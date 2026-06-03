# Cyclope Central

Cyclope Central is the initial secure foundation for a private, self-hosted MSP/RMM platform.

## Scope

This repository intentionally implements only the platform foundation:

- Multi-tenant data model boundaries
- FastAPI backend with health and version endpoints
- PostgreSQL and Redis development services
- Next.js dashboard shell with dark mode
- Go endpoint agent skeleton for safe check-in telemetry

Remote access, command execution, and PowerShell execution are not implemented.

## Repository Structure

```text
frontend/        Next.js 16 dashboard
backend/         FastAPI, SQLAlchemy, Alembic backend
agent/           Go endpoint agent skeleton
infrastructure/  Future IaC and self-hosted deployment assets
docker/          Container build files
docs/            Architecture and development documentation
scripts/         Developer helper scripts
```

## Quick Start

```bash
docker compose up --build
```

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000/api/health>
- Backend docs: <http://localhost:8000/docs>


## Authentication and RBAC

Operator APIs and the dashboard now use password-based login with hashed passwords, short-lived access tokens, refresh token rotation/revocation, and role-based permissions. Users are scoped to one organization, and server-side checks enforce tenant boundaries for devices, inventory, alerts, jobs, notification settings, and user management. Roles are `viewer`, `technician`, `admin`, and `owner`; remote access, scripting, remote shell, and remote desktop remain out of scope.

## Endpoint Inventory

Authenticated check-ins can include read-only inventory snapshots. Cyclope Central stores the latest hardware, disk, network, software, security, and update posture per device while preserving lightweight historical check-in records. Inventory collection deliberately excludes user documents, browser history, passwords, cookies, Wi-Fi passwords, credential material, keystrokes, screenshots, and user activity.

The dashboard device detail page exposes tabs for Overview, Hardware, Network, Software, Security, Updates, and Check-ins.

## Device Health Alerts

Cyclope Central evaluates read-only check-in and inventory data into deterministic alerts for offline devices, low disk space, high memory usage, disabled Defender/firewall, pending reboot, stale Windows updates, outdated agents, and stale inventory. Alerts support active, acknowledged, and resolved states with immutable lifecycle events. No alert path introduces remote command execution, remote shell, PowerShell execution, or remote desktop.



## Alert Notifications

Cyclope Central can enqueue tenant-scoped alert notifications through configurable email and webhook channels. Notification rules can filter by alert severity and alert rule key, disabled channels/rules are skipped, webhook secret headers are masked in API responses, and delivery attempts are tracked with pending, sent, failed, and skipped states. Delivery failures are recorded safely and do not break alert creation.

## Safe Agent Jobs

Cyclope Central now supports auditable, predefined agent jobs for enrolled devices. Operators may create only the built-in job types `ping`, `refresh_inventory`, `collect_agent_logs`, and `get_service_status`; each job is tenant-scoped, expires after a configurable timeout, and records lifecycle events for creation, assignment, start, completion, failure, cancellation, and expiration.

Agents poll using their existing `device_id` and `device_secret`, run only local built-in handlers, and return bounded stdout-style summaries. The framework explicitly rejects arbitrary commands, script text, PowerShell, remote shells, remote desktop, file transfer jobs, credential collection, and hidden persistence.

## Enrollment and Check-in Workflow

1. Start the local database and backend, then run Alembic migrations.
2. Create a limited-use enrollment token. The command prints the plaintext token once; only its hash is stored.
3. Run `cyclope-agent enroll <token>` on the endpoint. The backend returns a device-specific secret, and the agent stores it in `cyclope-agent.json` with `0600` permissions.
4. Run `cyclope-agent checkin` or `cyclope-agent run`. Check-ins authenticate with `device_id` and `device_secret`, update inventory status, and write audit events.

```bash
cd backend && alembic upgrade head
PYTHONPATH=backend ./scripts/create-enrollment-token.py --organization default --max-uses 1
cd agent && CYCLOPE_AGENT_CONFIG=cyclope-agent.json go run ./cmd/cyclope-agent enroll <printed-token>
cd agent && CYCLOPE_AGENT_CONFIG=cyclope-agent.json go run ./cmd/cyclope-agent checkin
```

Secrets are never logged by the backend or agent, and remote access, command execution, PowerShell execution, and remote desktop are out of scope.

## Local Checks

```bash
cd backend && python -m compileall app
cd frontend && npm install && npm run build
cd agent && go test ./...
```
