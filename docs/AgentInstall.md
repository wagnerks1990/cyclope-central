# Cyclope Central Windows Agent Installation

Cyclope Central's endpoint agent is designed for authenticated check-ins, read-only inventory, and the narrow safe job framework (`ping`, `refresh_inventory`, `collect_agent_logs`, and `get_service_status`). It does **not** implement arbitrary command execution, PowerShell execution from the server, remote shell, remote desktop, credential collection, or file transfer jobs.

## Build the Windows agent

From Linux or macOS with Go installed:

```bash
./scripts/build-agent-windows.sh
```

The build script cross-compiles `agent/cmd/cyclope-agent` for Windows amd64 and writes:

- `dist/agent/windows/amd64/cyclope-agent.exe`
- `dist/agent/windows/amd64/cyclope-agent.exe.sha256`

Copy the executable and the installer script to the target host or to your deployment share.

## CLI commands

The Windows binary exposes explicit operational commands:

```powershell
.\cyclope-agent.exe version
.\cyclope-agent.exe --config C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json enroll
.\cyclope-agent.exe --config C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json checkin
.\cyclope-agent.exe --config C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json jobs
.\cyclope-agent.exe --config C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json config show
.\cyclope-agent.exe --config C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json service install
.\cyclope-agent.exe --config C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json service start
.\cyclope-agent.exe --config C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json service stop
.\cyclope-agent.exe --config C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json service uninstall
```

`config show` redacts stored bearer material such as the device secret. Do not paste unredacted config files into tickets or chat.

## PowerShell installer usage

Run PowerShell as Administrator, place `cyclope-agent.exe` next to `scripts/windows/install-agent.ps1` or build it under `dist/agent/windows/amd64/`, then run:

```powershell
.\scripts\windows\install-agent.ps1 `
  -ServerUrl "https://cyclope.example.com" `
  -EnrollmentToken "paste-one-time-enrollment-token" `
  -OrganizationLabel "Acme Corp"
```

The installer:

1. Creates `C:\Program Files\Cyclope Central\Agent` for the binary.
2. Creates `C:\ProgramData\CyclopeCentral\Agent` for config and logs.
3. Writes a local config with the backend API URL, check-in interval, job polling interval, and log path.
4. Passes the enrollment token through a child-process environment variable so the token is not printed.
5. Enrolls the agent, saving only the returned device credentials in the local config.
6. Installs `CyclopeCentralAgent` with automatic startup and starts it.

Optional interval and RustDesk configuration flags:

```powershell
.\scripts\windows\install-agent.ps1 `
  -ServerUrl "https://cyclope.example.com" `
  -EnrollmentToken "paste-one-time-enrollment-token" `
  -CheckinIntervalSeconds 300 `
  -JobIntervalSeconds 60 `
  -RustDeskServerHost "rustdesk.example.com" `
  -RustDeskRelayHost "rustdesk.example.com" `
  -RustDeskPublicKey "paste-public-key"
```

RustDesk is not downloaded by this installer. To install RustDesk during the same local workflow, provide `-RustDeskInstallerPath` with a trusted local installer path; otherwise the script only configures an existing RustDesk installation.

## Manual install steps

1. Build the Windows binary with `./scripts/build-agent-windows.sh`.
2. Copy `cyclope-agent.exe` to `C:\Program Files\Cyclope Central\Agent\`.
3. Create `C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json` from `agent/cyclope-agent.example.json`.
4. Set `api_base_url` to your backend API URL, for example `https://cyclope.example.com/api`.
5. Set `log_path` to `C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.log`.
6. Enroll without printing the token:

   ```powershell
   $env:CYCLOPE_ENROLLMENT_TOKEN = "paste-one-time-enrollment-token"
   & "C:\Program Files\Cyclope Central\Agent\cyclope-agent.exe" --config "C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json" enroll
   Remove-Item Env:\CYCLOPE_ENROLLMENT_TOKEN
   ```

7. Install and start the service:

   ```powershell
   & "C:\Program Files\Cyclope Central\Agent\cyclope-agent.exe" --config "C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json" service install
   & "C:\Program Files\Cyclope Central\Agent\cyclope-agent.exe" --config "C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json" service start
   ```

## Uninstall

Run as Administrator:

```powershell
.\scripts\windows\uninstall-agent.ps1
```

By default, the uninstall script removes the service and binary while preserving config and logs. Add `-RemoveConfig` only when you intentionally want to delete local enrollment state and troubleshooting logs:

```powershell
.\scripts\windows\uninstall-agent.ps1 -RemoveConfig
```

## Troubleshooting

- Default log file: `C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.log`
- Verify service state:

  ```powershell
  Get-Service CyclopeCentralAgent
  ```

- Send one check-in manually:

  ```powershell
  & "C:\Program Files\Cyclope Central\Agent\cyclope-agent.exe" --config "C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json" checkin
  ```

- Process safe built-in jobs once:

  ```powershell
  & "C:\Program Files\Cyclope Central\Agent\cyclope-agent.exe" --config "C:\ProgramData\CyclopeCentral\Agent\cyclope-agent.json" jobs
  ```

## Safe enrollment notes

- Treat enrollment tokens as short-lived secrets.
- Do not store enrollment tokens in config files, ticket systems, screenshots, or logs.
- The backend stores only hashed enrollment tokens and hashed device secrets.
- The agent `config show` command masks stored credentials.
- The service only performs authenticated telemetry, read-only inventory, approved built-in jobs, and RustDesk status reporting; no server response is executed as a command or script.
