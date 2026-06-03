# Architecture

Cyclope Central is designed as a self-hosted, security-first MSP/RMM control plane.

## Core Principles

- **Tenant isolation:** every operational entity is scoped to an organization.
- **Least privilege:** authentication and authorization are first-class extension points.
- **Auditability:** sensitive operator and platform events will be captured in `AuditLog`.
- **Safe agent design:** the agent skeleton supports check-ins only. Remote access, command execution, and PowerShell execution are intentionally absent.
- **Self-hosted operations:** Docker Compose provides the local development baseline and can evolve into production deployment recipes.

## Components

### Frontend

The frontend uses Next.js 16, TypeScript, Tailwind CSS, and shadcn/ui-compatible primitives. It includes a responsive dark dashboard, login page, device list placeholder, and settings placeholder.

### Backend

The backend uses FastAPI, SQLAlchemy, Alembic, PostgreSQL, and Redis. Current endpoints expose platform health, version metadata, and a JWT plumbing stub.

### Agent

The agent is a Go module with configuration loading, structured logging, a Windows service expansion point, and a check-in framework stub. Linux support is reserved via non-Windows service files.

### Data Model

Initial models include:

- `Organization`
- `User`
- `Device`
- `Agent`
- `DeviceCheckin`
- `AuditLog`


## Tenant and Permission Model

Dashboard users authenticate with password credentials; only PBKDF2 password hashes are stored. Login returns a short-lived JWT access token plus a random refresh token whose hash is stored server-side for rotation and logout/revocation. Passwords, password hashes, access tokens, refresh tokens, and refresh token hashes are not returned by user APIs.

Every operator-facing API resolves the authenticated user and scopes reads/writes to `user.organization_id`. The RBAC model is additive: `viewer` can read dashboard/devices/alerts, `technician` can also acknowledge alerts and create/cancel safe jobs, `admin` can also manage notification channels/rules, and `owner` can also manage users and organization settings. Agent enrollment/check-in remains credentialed separately by enrollment tokens and device secrets.

## Agent Enrollment Security Model

Enrollment uses organization-scoped, limited-use tokens. Plaintext enrollment tokens are shown only at creation time and the database stores only HMAC-SHA256 token hashes. Tokens can expire, be revoked, and enforce maximum use counts.

After enrollment, each device receives a device-specific secret. Only the hash of that secret is stored server-side. Check-ins must present both `device_id` and the secret, and failures return a generic authentication error so callers cannot distinguish an unknown device from an incorrect secret.

Successful enrollments and check-ins write `AuditLog` entries. Check-ins update device hostname, OS, architecture, IP, agent version, health, online status, and last-seen timestamps. The protocol accepts inventory and health telemetry only; remote access, shell, PowerShell, remote desktop, and command execution are not part of the model.

## Inventory Data Flow

The endpoint agent performs safe, read-only local inventory collection during check-in. On Windows, collection reads local system APIs and registry locations for OS metadata, installed software, firewall/Defender posture, pending reboot markers, and update state without launching remote commands, forcing Windows Update scans, executing PowerShell, collecting user documents, reading browser data, or accessing credential material. Linux inventory remains a future expansion point.

The backend accepts inventory as part of authenticated check-ins, stores only the latest normalized inventory tables for each device, and keeps historical `DeviceCheckin` records small by storing an inventory refresh marker instead of duplicating large software lists. The dashboard retrieves inventory through dedicated read APIs for hardware/network, software, security, and updates.

## Alert Evaluation Flow

After each authenticated check-in and inventory refresh, the backend evaluates tenant-scoped default alert rules against the latest read-only device state. Rule evaluation creates one active alert per device/rule, writes repeated-detection events instead of duplicating active alerts, and auto-resolves active or acknowledged alerts when conditions clear. Operators can acknowledge or manually resolve alerts through API/dashboard actions, each of which appends an `AlertEvent`.

Alerting is deterministic and server-side only: rules inspect stored check-in and inventory facts and never instruct agents to execute commands, launch shells, run PowerShell, or start remote desktop sessions.



## Notification Delivery Flow

When alert evaluation creates a new alert, Cyclope Central evaluates enabled tenant notification rules. Matching rules enqueue `NotificationDelivery` rows for enabled email or webhook channels; repeated detections on an already-active alert append alert events but do not enqueue duplicate notification deliveries. A separate delivery service processes pending rows, applies retry limits and timeouts, records attempts and sanitized failures, and marks deliveries as sent, failed, or skipped.

Webhook delivery posts a bounded JSON document describing the alert and never executes responses. Webhook header secrets remain in channel configuration only and are masked in API responses. Email delivery uses SMTP settings from environment variables. Notification delivery does not add remote command execution, scripting, remote shell, or remote desktop behavior.

## Safe Job Lifecycle

Agent jobs are predefined, tenant-scoped work items attached to a device. Operators create jobs through device APIs, the backend validates the requested job type and payload, assigns unexpired queued jobs only to the authenticated agent for that same device, and records `AgentJobEvent` rows for every lifecycle transition. Terminal states are `succeeded`, `failed`, `canceled`, and `expired`; non-terminal jobs are automatically expired when their timeout passes.

Allowed job types are intentionally narrow: `ping`, `refresh_inventory`, `collect_agent_logs`, and `get_service_status`. Payload validation is per-job-type and never accepts shell commands, scripts, PowerShell text, remote desktop requests, file transfer instructions, credential collection, or arbitrary server-provided actions. Agent-side handlers mirror the server allow-list and reject unknown job types locally before returning auditable results.

The `refresh_inventory` job reuses the existing read-only inventory/check-in path. `collect_agent_logs` is bounded to recent agent log lines only. `get_service_status` accepts a validated service name and checks status locally without executing commands.

## Future Expansion Points

- OIDC/SAML identity providers
- Tenant-scoped RBAC and policy enforcement
- Signed agent enrollment and key rotation
- Inventory and posture telemetry ingestion
- Production infrastructure modules

## RustDesk OSS Remote Access

RustDesk OSS is integrated as an external remote desktop provider. Cyclope Central stores tenant-scoped provider configuration, device RustDesk IDs reported by authenticated check-ins, and launch audit events. The dashboard opens `rustdesk://` links after the backend authorizes and audits the launch. Cyclope Central does not implement screen capture, keyboard injection, custom remote desktop transport, arbitrary command execution, or server-driven PowerShell.
