<#
.SYNOPSIS
Stops and removes the Cyclope Central Windows agent service.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$InstallDir = "$env:ProgramFiles\Cyclope Central\Agent",

    [Parameter(Mandatory = $false)]
    [string]$ProgramDataDir = "$env:ProgramData\CyclopeCentral\Agent",

    [Parameter(Mandatory = $false)]
    [string]$ServiceName = "CyclopeCentralAgent",

    [Parameter(Mandatory = $false)]
    [switch]$RemoveConfig
)

$ErrorActionPreference = "Stop"
$AgentExe = Join-Path $InstallDir "cyclope-agent.exe"
$ConfigPath = Join-Path $ProgramDataDir "cyclope-agent.json"

Write-Host "Stopping Cyclope Central Agent service if it is running..."
if (Test-Path $AgentExe) {
    & $AgentExe --config $ConfigPath service stop
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Service stop returned exit code $LASTEXITCODE; continuing with uninstall."
    }

    & $AgentExe --config $ConfigPath service uninstall
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Service uninstall returned exit code $LASTEXITCODE. It may already be removed."
    }
}
else {
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($null -ne $service) {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        sc.exe delete $ServiceName | Out-Null
    }
}

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}

if ($RemoveConfig -and (Test-Path $ProgramDataDir)) {
    Remove-Item -Recurse -Force $ProgramDataDir
    Write-Host "Removed agent configuration and logs."
}
else {
    Write-Host "Preserved agent configuration and logs in $ProgramDataDir. Use -RemoveConfig to delete them."
}

Write-Host "Cyclope Central Agent uninstall workflow completed."
