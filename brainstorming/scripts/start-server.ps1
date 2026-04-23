<#
.SYNOPSIS
    Start the brainstorm server and output connection info.
.DESCRIPTION
    Starts server on a random high port, outputs JSON with URL.
    Each session gets its own directory to avoid conflicts.
    PowerShell equivalent of start-server.sh for Windows environments.
.PARAMETER ProjectDir
    Store session files under <path>\.superpowers\brainstorm\
    instead of $env:TEMP. Files persist after server stops.
.PARAMETER Host
    Host/interface to bind (default: 127.0.0.1).
    Use 0.0.0.0 in remote/containerized environments.
.PARAMETER UrlHost
    Hostname shown in returned URL JSON.
.PARAMETER Foreground
    Run server in the current terminal (no backgrounding).
.PARAMETER Background
    Force background mode.
.EXAMPLE
    .\start-server.ps1
    .\start-server.ps1 -ProjectDir "D:\MyProject" -Host "127.0.0.1" -Foreground
#>
# -*- coding: utf-8 -*-
[CmdletBinding()]
param(
    [string]$ProjectDir = '',
    [Alias('BindHost')]
    [string]$Host = '127.0.0.1',
    [string]$UrlHost = '',
    [switch]$Foreground,
    [switch]$Background
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Resolve URL host
if ([string]::IsNullOrEmpty($UrlHost)) {
    if ($Host -eq '127.0.0.1' -or $Host -eq 'localhost') {
        $UrlHost = 'localhost'
    } else {
        $UrlHost = $Host
    }
}

# Generate unique session directory
$SessionId = "$PID-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"

if (-not [string]::IsNullOrEmpty($ProjectDir)) {
    $SessionDir = Join-Path $ProjectDir ".superpowers\brainstorm\$SessionId"
} else {
    $SessionDir = Join-Path $env:TEMP "brainstorm-$SessionId"
}

$StateDir   = Join-Path $SessionDir 'state'
$ContentDir = Join-Path $SessionDir 'content'
$PidFile    = Join-Path $StateDir 'server.pid'
$LogFile    = Join-Path $StateDir 'server.log'

# Create fresh session directory with content and state peers
New-Item -ItemType Directory -Path $ContentDir -Force | Out-Null
New-Item -ItemType Directory -Path $StateDir -Force | Out-Null

# Kill any existing server from a previous session using same PID file
if (Test-Path $PidFile) {
    $oldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        try {
            Stop-Process -Id ([int]$oldPid) -Force -ErrorAction SilentlyContinue
        } catch {
            # Process may already be gone
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# Build environment variables for server.cjs
$serverEnv = @{
    'BRAINSTORM_DIR'      = $SessionDir
    'BRAINSTORM_HOST'     = $Host
    'BRAINSTORM_URL_HOST' = $UrlHost
    'BRAINSTORM_OWNER_PID'= $PID.ToString()
}

# Set environment for child process
foreach ($kv in $serverEnv.GetEnumerator()) {
    [System.Environment]::SetEnvironmentVariable($kv.Key, $kv.Value, 'Process')
}

$serverCjs = Join-Path $ScriptDir 'server.cjs'

# Foreground mode
if ($Foreground.IsPresent) {
    Set-Content -Path $PidFile -Value $PID -Encoding UTF8
    & node $serverCjs
    exit $LASTEXITCODE
}

# Background mode: start server as a background job
$proc = Start-Process -FilePath 'node' `
    -ArgumentList $serverCjs `
    -WorkingDirectory $ScriptDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError (Join-Path $StateDir 'server.err.log') `
    -PassThru

$serverPid = $proc.Id
Set-Content -Path $PidFile -Value $serverPid -Encoding UTF8

# Wait for server-started message (check log file, up to 5 seconds)
$maxAttempts = 50
for ($i = 0; $i -lt $maxAttempts; $i++) {
    if (Test-Path $LogFile) {
        $logContent = Get-Content $LogFile -Raw -ErrorAction SilentlyContinue
        if ($logContent -and $logContent -match 'server-started') {
            # Verify server is still alive after a short window
            Start-Sleep -Milliseconds 500
            $alive = $false
            try {
                $p = Get-Process -Id $serverPid -ErrorAction Stop
                if (-not $p.HasExited) {
                    $alive = $true
                }
            } catch {
                # Process gone
            }

            if (-not $alive) {
                $retryCmd = "$ScriptDir\start-server.ps1"
                if (-not [string]::IsNullOrEmpty($ProjectDir)) { $retryCmd += " -ProjectDir `"$ProjectDir`"" }
                $retryCmd += " -Host $Host -UrlHost $UrlHost -Foreground"
                Write-Output "{`"error`": `"Server started but was killed. Retry with: $retryCmd`"}"
                exit 1
            }

            # Output the server-started JSON line
            $lines = Get-Content $LogFile -Encoding UTF8
            $startedLine = $lines | Where-Object { $_ -match 'server-started' } | Select-Object -First 1
            Write-Output $startedLine
            exit 0
        }
    }
    Start-Sleep -Milliseconds 100
}

# Timeout
Write-Output '{"error": "Server failed to start within 5 seconds"}'
exit 1
