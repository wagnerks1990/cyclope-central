<#
.SYNOPSIS
Installs and enrolls the Cyclope Central Windows agent.

.DESCRIPTION
The installer writes a local config under ProgramData, enrolls the agent using the
provided enrollment token, installs the Windows service, and starts it. The token
is passed through a child-process environment variable and is never printed.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ServerUrl,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$EnrollmentToken,

    [Parameter(Mandatory = $false)]
    [string]$OrganizationLabel = "",

    [Parameter(Mandatory = $false)]
    [string]$InstallDir = "$env:ProgramFiles\Cyclope Central\Agent",

    [Parameter(Mandatory = $false)]
    [string]$ProgramDataDir = "$env:ProgramData\CyclopeCentral\Agent",

    [Parameter(Mandatory = $false)]
    [ValidateRange(60, 86400)]
    [int]$CheckinIntervalSeconds = 300,

    [Parameter(Mandatory = $false)]
    [ValidateRange(15, 86400)]
    [int]$JobIntervalSeconds = 60
)

$ErrorActionPreference = "Stop"
$ServiceName = "CyclopeCentralAgent"
$ConfigPath = Join-Path $ProgramDataDir "cyclope-agent.json"
$LogPath = Join-Path $ProgramDataDir "cyclope-agent.log"
$InstallExe = Join-Path $InstallDir "cyclope-agent.exe"
$CandidateExes = @(
    (Join-Path $PSScriptRoot "cyclope-agent.exe"),
    (Join-Path $PSScriptRoot "..\..\dist\agent\windows\amd64\cyclope-agent.exe")
)

function Resolve-ApiBaseUrl {
    param([string]$Url)
    $trimmed = $Url.TrimEnd('/')
    if ($trimmed.ToLowerInvariant().EndsWith('/api')) {
        return $trimmed
    }
    return "$trimmed/api"
}

function Resolve-AgentSource {
    foreach ($candidate in $CandidateExes) {
        $fullPath = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Path $fullPath) {
            return $fullPath
        }
    }
    throw "cyclope-agent.exe was not found next to the installer or in dist\agent\windows\amd64."
}

Write-Host "Installing Cyclope Central Agent service..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ProgramDataDir | Out-Null

$sourceExe = Resolve-AgentSource
Copy-Item -Force -Path $sourceExe -Destination $InstallExe

$config = [ordered]@{
    tenant_id = $OrganizationLabel
    install_id = [guid]::NewGuid().ToString()
    device_id = ""
    device_secret = ""
    api_base_url = (Resolve-ApiBaseUrl -Url $ServerUrl)
    agent_token = ""
    log_level = "INFO"
    log_path = $LogPath
    service_name = $ServiceName
    checkin_interval_seconds = $CheckinIntervalSeconds
    job_interval_seconds = $JobIntervalSeconds
}
$config | ConvertTo-Json -Depth 4 | Set-Content -NoNewline -Encoding UTF8 -Path $ConfigPath

try {
    $env:CYCLOPE_ENROLLMENT_TOKEN = $EnrollmentToken
    & $InstallExe --config $ConfigPath enroll
    if ($LASTEXITCODE -ne 0) {
        throw "agent enrollment failed with exit code $LASTEXITCODE"
    }
}
finally {
    Remove-Item Env:\CYCLOPE_ENROLLMENT_TOKEN -ErrorAction SilentlyContinue
}

& $InstallExe --config $ConfigPath service install
if ($LASTEXITCODE -ne 0) {
    throw "service install failed with exit code $LASTEXITCODE"
}

& $InstallExe --config $ConfigPath service start
if ($LASTEXITCODE -ne 0) {
    throw "service start failed with exit code $LASTEXITCODE"
}

Write-Host "Cyclope Central Agent installed and started. Logs: $LogPath"
