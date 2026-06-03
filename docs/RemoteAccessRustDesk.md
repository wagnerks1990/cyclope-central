# RustDesk OSS Remote Access Integration

Cyclope Central integrates RustDesk OSS as an external remote desktop provider. Cyclope Central remains the MSP dashboard for tenant scoping, RBAC, device inventory, launch auditing, and operator workflows; RustDesk provides the remote desktop transport.

Cyclope Central does **not** implement custom remote desktop, screen capture, keylogging, arbitrary command execution, server-driven PowerShell, credential collection, or remote shell behavior.

## Docker Compose deployment

`docker-compose.yml` includes two RustDesk services using the official RustDesk server image:

- `rustdesk-hbbs` for rendezvous/ID brokering.
- `rustdesk-hbbr` for relay traffic.

Both services persist their data and generated keys in the `rustdesk-data` named volume. Configure the public host values in your `.env` file:

```dotenv
RUSTDESK_SERVER_HOST=rustdesk.example.com
RUSTDESK_RELAY_HOST=rustdesk.example.com
RUSTDESK_PUBLIC_KEY=<public-key-generated-by-rustdesk-server>
```

Start the stack as usual:

```bash
docker compose up --build
```

## Ports, firewall, and NAT

Expose/forward the following ports from the public RustDesk host to the Docker host:

| Port | Protocol | Purpose |
| --- | --- | --- |
| 21115 | TCP | RustDesk hbbs TCP service |
| 21116 | TCP | RustDesk hbbs TCP rendezvous |
| 21116 | UDP | RustDesk hbbs NAT traversal |
| 21117 | TCP | RustDesk hbbr relay |
| 21118 | TCP | RustDesk web/client support |
| 21119 | TCP | RustDesk web/client support |

For NAT deployments, `RUSTDESK_SERVER_HOST` and `RUSTDESK_RELAY_HOST` must resolve to the public address clients can reach. Do not expose these ports through an HTTP-only reverse proxy; RustDesk requires raw TCP/UDP forwarding. A reverse proxy may still terminate HTTPS for Cyclope Central's dashboard/API separately.

## Backend configuration workflow

Operators with remote-provider management permission can create a RustDesk provider through:

```http
POST /api/remote/providers
```

The provider stores the RustDesk host, relay host, public key, enabled state, and provider type `rustdesk_oss`. Device check-ins update `RemoteDeviceLink` with the endpoint's RustDesk installation status and RustDesk ID. Launches through `/api/devices/{device_id}/remote/launch` create both remote session audit rows and normal audit log events.

RBAC boundaries:

- `viewer`: can view remote status, cannot launch.
- `technician`, `admin`, `owner`: can launch RustDesk sessions.
- `admin`, `owner`: can manage remote provider configuration.

## Agent and RustDesk install workflow

The Cyclope agent detects local RustDesk installation/status and reports the RustDesk ID during normal authenticated check-ins. It only reads local RustDesk metadata and does not download binaries or execute server-provided commands.

The Windows agent installer supports optional RustDesk parameters:

```powershell
.\scripts\windows\install-agent.ps1 `
  -ServerUrl "https://central.example.com" `
  -EnrollmentToken "paste-one-time-token" `
  -RustDeskServerHost "rustdesk.example.com" `
  -RustDeskRelayHost "rustdesk.example.com" `
  -RustDeskPublicKey "paste-public-key"
```

RustDesk is **not** installed automatically unless a local installer path is explicitly provided:

```powershell
.\scripts\windows\install-agent.ps1 `
  -ServerUrl "https://central.example.com" `
  -EnrollmentToken "paste-one-time-token" `
  -RustDeskInstallerPath "C:\Installers\rustdesk-host.exe" `
  -RustDeskServerHost "rustdesk.example.com" `
  -RustDeskRelayHost "rustdesk.example.com" `
  -RustDeskPublicKey "paste-public-key"
```

The script attempts a silent install for the local RustDesk installer if supported. If silent install is unsupported, install RustDesk manually and rerun with the RustDesk configuration arguments. RustDesk keys are not printed by the script.

## Dashboard launch and manual fallback

The Device Detail page includes a **Remote Access** tab. If the agent has reported a RustDesk ID, the dashboard can request a launch audit event and then open a `rustdesk://` URL. If the browser blocks the protocol handler, open RustDesk locally and manually connect to the displayed RustDesk ID.

## Security boundaries

- RustDesk is the only remote desktop provider in this integration.
- Cyclope Central does not proxy screen contents or keyboard input.
- The agent does not execute remote desktop commands from the server.
- Do not store RustDesk private keys, credentials, passwords, or browser/user data in Cyclope Central.
- Treat RustDesk public key and host settings as configuration; do not print or log key material in scripts or support output.
