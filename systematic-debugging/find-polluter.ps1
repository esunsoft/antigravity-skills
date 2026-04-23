<#
.SYNOPSIS
    Bisection script to find which test creates unwanted files/state.
.DESCRIPTION
    Runs test files one by one and checks if a specified file or directory
    appears after each test execution. Reports the polluting test.
    PowerShell equivalent of find-polluter.sh for Windows environments.
.PARAMETER PollutionCheck
    The file or directory path to check for (e.g., '.git', 'temp_output').
.PARAMETER TestPattern
    Glob pattern for test files (e.g., 'src\**\*.test.ts').
.EXAMPLE
    .\find-polluter.ps1 -PollutionCheck ".git" -TestPattern "src\**\*.test.ts"
#>
# -*- coding: utf-8 -*-
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$PollutionCheck,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$TestPattern
)

$ErrorActionPreference = 'Continue'

Write-Host "🔍 Searching for test that creates: $PollutionCheck" -ForegroundColor Cyan
Write-Host "Test pattern: $TestPattern"
Write-Host ""

# Get list of test files
$testFiles = Get-ChildItem -Path . -Filter (Split-Path $TestPattern -Leaf) -Recurse |
    Where-Object { $_.FullName -like "*$($TestPattern.Replace('\','/'))*" -or $_.FullName -like "*$TestPattern*" } |
    Sort-Object FullName

if (-not $testFiles -or $testFiles.Count -eq 0) {
    # Fallback: try direct glob
    $testFiles = Get-ChildItem -Path $TestPattern -ErrorAction SilentlyContinue | Sort-Object FullName
}

$total = @($testFiles).Count
Write-Host "Found $total test files"
Write-Host ""

if ($total -eq 0) {
    Write-Host "No test files found matching pattern: $TestPattern" -ForegroundColor Yellow
    exit 1
}

$count = 0
foreach ($testFile in $testFiles) {
    $count++
    $relativePath = $testFile.FullName

    # Skip if pollution already exists
    if (Test-Path $PollutionCheck) {
        Write-Host "⚠️  Pollution already exists before test $count/$total" -ForegroundColor Yellow
        Write-Host "   Skipping: $relativePath"
        continue
    }

    Write-Host "[$count/$total] Testing: $relativePath"

    # Run the test (suppress output)
    try {
        & npm test $relativePath 2>&1 | Out-Null
    } catch {
        # Test failure is OK — we're just looking for pollution
    }

    # Check if pollution appeared
    if (Test-Path $PollutionCheck) {
        Write-Host ""
        Write-Host "🎯 FOUND POLLUTER!" -ForegroundColor Red -BackgroundColor Black
        Write-Host "   Test: $relativePath" -ForegroundColor Red
        Write-Host "   Created: $PollutionCheck" -ForegroundColor Red
        Write-Host ""

        Write-Host "Pollution details:"
        $item = Get-Item $PollutionCheck
        Write-Host ("   Type: {0}" -f $(if ($item.PSIsContainer) { 'Directory' } else { 'File' }))
        Write-Host ("   Size: {0}" -f $(if ($item.PSIsContainer) { "{0} items" -f (Get-ChildItem $item -Recurse).Count } else { "{0:N0} bytes" -f $item.Length }))
        Write-Host ("   Created: {0}" -f $item.CreationTime)
        Write-Host ""

        Write-Host "To investigate:"
        Write-Host "  npm test $relativePath    # Run just this test"
        Write-Host "  Get-Content $relativePath  # Review test code"
        exit 1
    }
}

Write-Host ""
Write-Host "✅ No polluter found — all tests clean!" -ForegroundColor Green
exit 0
