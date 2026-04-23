<#
.SYNOPSIS
    Bundle a React app into a single HTML artifact file.
.DESCRIPTION
    Builds the project with Parcel and inlines all assets into a single
    HTML file suitable for use as a Claude artifact.
    PowerShell equivalent of bundle-artifact.sh for Windows environments.
.EXAMPLE
    .\bundle-artifact.ps1
    # Run from the project root directory
#>
# -*- coding: utf-8 -*-
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

Write-Host "📦 Bundling React app to single HTML artifact..." -ForegroundColor Cyan

# Check if we're in a project directory
if (-not (Test-Path 'package.json')) {
    Write-Host "❌ Error: No package.json found. Run this script from your project root." -ForegroundColor Red
    exit 1
}

# Check if index.html exists
if (-not (Test-Path 'index.html')) {
    Write-Host "❌ Error: No index.html found in project root." -ForegroundColor Red
    Write-Host "   This script requires an index.html entry point."
    exit 1
}

# Install bundling dependencies
Write-Host "📦 Installing bundling dependencies..." -ForegroundColor Cyan
& pnpm add -D parcel '@parcel/config-default' parcel-resolver-tspaths html-inline
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install bundling dependencies" -ForegroundColor Red
    exit 1
}

# Create Parcel config with tspaths resolver
if (-not (Test-Path '.parcelrc')) {
    Write-Host "🔧 Creating Parcel configuration with path alias support..."
    @'
{
  "extends": "@parcel/config-default",
  "resolvers": ["parcel-resolver-tspaths", "..."]
}
'@ | Set-Content -Path '.parcelrc' -Encoding UTF8
}

# Clean previous build
Write-Host "🧹 Cleaning previous build..."
if (Test-Path 'dist') { Remove-Item 'dist' -Recurse -Force }
if (Test-Path 'bundle.html') { Remove-Item 'bundle.html' -Force }

# Build with Parcel
Write-Host "🔨 Building with Parcel..." -ForegroundColor Cyan
& pnpm exec parcel build index.html --dist-dir dist --no-source-maps
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Parcel build failed" -ForegroundColor Red
    exit 1
}

# Inline everything into single HTML
Write-Host "🎯 Inlining all assets into single HTML file..."
& pnpm exec html-inline dist/index.html | Set-Content -Path 'bundle.html' -Encoding UTF8
if (-not (Test-Path 'bundle.html') -or (Get-Item 'bundle.html').Length -eq 0) {
    Write-Host "❌ Failed to create bundle.html" -ForegroundColor Red
    exit 1
}

# Get file size (human-readable)
$fileSize = (Get-Item 'bundle.html').Length
$fileSizeFormatted = if ($fileSize -gt 1MB) {
    "{0:N1} MB" -f ($fileSize / 1MB)
} elseif ($fileSize -gt 1KB) {
    "{0:N1} KB" -f ($fileSize / 1KB)
} else {
    "$fileSize bytes"
}

Write-Host ""
Write-Host "✅ Bundle complete!" -ForegroundColor Green
Write-Host "📄 Output: bundle.html ($fileSizeFormatted)"
Write-Host ""
Write-Host "You can now use this single HTML file as an artifact in Claude conversations."
Write-Host "To test locally: open bundle.html in your browser"
