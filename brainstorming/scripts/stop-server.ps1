<#
.SYNOPSIS
    Stop the brainstorm server and clean up.
.DESCRIPTION
    Kills the server process. Only deletes session directory if it's
    under $env:TEMP (ephemeral). Persistent directories (.superpowers/) are
    kept so mockups can be reviewed later.
    PowerShell equivalent of stop-server.sh for Windows environments.
.PARAMETER SessionDir
    Path to the session directory to clean up.
.EXAMPLE
    .\stop-server.ps1 -SessionDir "C:\Users\user\AppData\Local\Temp\brainstorm-12345-1711111111"
#>
# -*- coding: utf-8 -*-
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$SessionDir
)

$ErrorActionPreference = 'Stop'

$StateDir = Join-Path $SessionDir 'state'
$PidFile  = Join-Path $StateDir 'server.pid'

if (-not (Test-Path $PidFile)) {
    Write-Output '{"status": "not_running"}'
    exit 0
}

$pid_value = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
if ([string]::IsNullOrEmpty($pid_value)) {
    Write-Output '{"status": "not_running"}'
    exit 0
}

$targetPid = [int]$pid_value

# Try to stop gracefully
try {
    $proc = Get-Process -Id $targetPid -ErrorAction Stop
    $proc.CloseMainWindow() | Out-Null
} catch {
    # Process already gone — clean up and exit
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    $serverLog = Join-Path $StateDir 'server.log'
    Remove-Item $serverLog -Force -ErrorAction SilentlyContinue
    Write-Output '{"status": "stopped"}'
    exit 0
}

# Wait for graceful shutdown (up to ~2s)
$stopped = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $proc = Get-Process -Id $targetPid -ErrorAction Stop
        if ($proc.HasExited) {
            $stopped = $true
            break
        }
    } catch {
        $stopped = $true
        break
    }
    Start-Sleep -Milliseconds 100
}

# If still running, escalate to force kill
if (-not $stopped) {
    try {
        Stop-Process -Id $targetPid -Force -ErrorAction Stop
        Start-Sleep -Milliseconds 200
    } catch {
        # Ignore — may have exited between check and kill
    }
}

# Final check
$stillRunning = $false
try {
    $proc = Get-Process -Id $targetPid -ErrorAction Stop
    if (-not $proc.HasExited) {
        $stillRunning = $true
    }
} catch {
    # Process is gone
}

if ($stillRunning) {
    Write-Output '{"status": "failed", "error": "process still running"}'
    exit 1
}

# Clean up
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
$serverLog = Join-Path $StateDir 'server.log'
Remove-Item $serverLog -Force -ErrorAction SilentlyContinue

# Only delete ephemeral temp directories
$tempDir = $env:TEMP
if ($SessionDir.StartsWith($tempDir, [System.StringComparison]::OrdinalIgnoreCase)) {
    Remove-Item $SessionDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output '{"status": "stopped"}'
