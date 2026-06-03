# Development

## Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Node.js 24+
- Go 1.23+

## Start the Stack

```bash
./scripts/dev-up.sh
```

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

Run migrations after PostgreSQL is available:

```bash
alembic upgrade head
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Agent

```bash
cd agent
go test ./...
go run ./cmd/cyclope-agent
```

Use `cyclope-agent.example.json` as the starting point for local configuration. The current agent only emits check-in stub logs.


## Local Bootstrap User

For local development, create an organization and first owner in a backend shell or migration seed, then use `/login` in the dashboard:

```bash
cd backend
python - <<'PY'
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User

db = SessionLocal()
org = Organization(name='Default MSP', slug='default')
db.add(org)
db.flush()
db.add(User(organization_id=org.id, email='owner@example.test', hashed_password=hash_password('ChangeMeNow!12345'), role='owner', is_active=True))
db.commit()
print(org.id)
db.close()
PY
```

Use that account to sign in, create lower-privilege users, and verify RBAC behavior. Never seed plaintext passwords or token values into source control.

## Enrollment and Check-in Commands

```bash
# after docker compose up and alembic upgrade head
PYTHONPATH=backend ./scripts/create-enrollment-token.py --organization default --ttl-hours 24 --max-uses 1

cd agent
cp cyclope-agent.example.json cyclope-agent.json
CYCLOPE_AGENT_CONFIG=cyclope-agent.json go run ./cmd/cyclope-agent enroll <printed-token>
CYCLOPE_AGENT_CONFIG=cyclope-agent.json go run ./cmd/cyclope-agent checkin
```

The agent stores `device_id` and `device_secret` locally after enrollment. Treat that file as sensitive endpoint credential material.

## Inventory Check-ins

After enrollment, a normal check-in sends the read-only inventory snapshot collected by the agent:

```bash
cd agent
CYCLOPE_AGENT_CONFIG=cyclope-agent.json go run ./cmd/cyclope-agent checkin
```

Use the dashboard device detail tabs or these API calls to inspect the latest inventory:

```bash
curl http://localhost:8000/api/devices/<device-id>/inventory
curl http://localhost:8000/api/devices/<device-id>/software
curl http://localhost:8000/api/devices/<device-id>/security
curl http://localhost:8000/api/devices/<device-id>/updates
```

Inventory collection is read-only. Do not add collection of user files, browser history, passwords, cookies, Wi-Fi passwords, screenshots, keystrokes, or user activity.

## Alert Testing Workflow

Generate alerts by enrolling an agent and posting a check-in with inventory conditions such as low disk free space or disabled Defender/firewall. Then inspect and transition alerts:

```bash
curl http://localhost:8000/api/dashboard/summary
curl 'http://localhost:8000/api/alerts?status=active'
curl -X POST http://localhost:8000/api/alerts/<alert-id>/acknowledge
curl -X POST http://localhost:8000/api/alerts/<alert-id>/resolve
curl http://localhost:8000/api/devices/<device-id>/alerts
```

Alert tests are deterministic and can be run with `cd backend && pytest`. Alerting remains read-only and must not add remote execution, shell, PowerShell, or remote desktop behavior.



## Notification Testing Workflow

Configure a local SMTP sink such as MailHog or a webhook capture service, then create channels and rules for an organization:

```bash
# Example local SMTP settings for backend environment
export CYCLOPE_SMTP_HOST=localhost
export CYCLOPE_SMTP_PORT=1025
export CYCLOPE_SMTP_FROM_EMAIL=cyclope-central@example.local

curl -X POST http://localhost:8000/api/notification-channels \
  -H 'Content-Type: application/json' \
  -d '{"organization_id":"<org-id>","name":"Ops Webhook","channel_type":"webhook","config":{"url":"https://webhook.site/<token>","headers":{"Authorization":"Bearer test-secret"}}}'

curl -X POST http://localhost:8000/api/notification-rules \
  -H 'Content-Type: application/json' \
  -d '{"organization_id":"<org-id>","name":"Critical alerts","severity_filter":["critical"],"channel_ids":["<channel-id>"]}'

curl http://localhost:8000/api/notifications/deliveries
```

Webhook responses are not executed and secret header values are masked by the API. Delivery processing is retryable and can be exercised from Python by importing `process_pending_deliveries` from `app.core.notifications` inside a backend shell or future worker.

## Safe Agent Job Workflow

Create and inspect jobs from the backend after a device has enrolled. Only the allow-listed job types are accepted:

```bash
curl -X POST http://localhost:8000/api/devices/<device-id>/jobs \
  -H 'Content-Type: application/json' \
  -d '{"job_type":"ping","payload":{}}'

curl -X POST http://localhost:8000/api/devices/<device-id>/jobs \
  -H 'Content-Type: application/json' \
  -d '{"job_type":"get_service_status","payload":{"service_name":"Spooler"}}'

curl http://localhost:8000/api/devices/<device-id>/jobs
curl -X POST http://localhost:8000/api/jobs/<job-id>/cancel
```

Run one polling cycle from the enrolled agent config, or use `run` for repeated check-ins and job polling:

```bash
cd agent
CYCLOPE_AGENT_CONFIG=cyclope-agent.json go run ./cmd/cyclope-agent jobs
CYCLOPE_AGENT_CONFIG=cyclope-agent.json go run ./cmd/cyclope-agent run
```

Job handlers must stay built-in and read-only. Do not add arbitrary commands, script execution, PowerShell, remote shell, remote desktop, file upload/download, credential collection, or persistence behavior.

## Security Notes

- Change all default secrets before deploying outside local development.
- Keep tenant identifiers on every data access path.
- Do not add remote access, shell, command, or PowerShell execution features without a dedicated security design review.
