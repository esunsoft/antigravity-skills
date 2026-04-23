<#
.SYNOPSIS
    Initialize a React + Vite + shadcn/ui project for Claude artifact creation.
.DESCRIPTION
    Creates a fully configured project with React 18, TypeScript, Vite,
    Tailwind CSS 3.4.1, and 40+ shadcn/ui components pre-installed.
    PowerShell equivalent of init-artifact.sh for Windows environments.
.PARAMETER ProjectName
    Name of the project directory to create.
.EXAMPLE
    .\init-artifact.ps1 -ProjectName "my-artifact"
#>
# -*- coding: utf-8 -*-
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ProjectName
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ===== Detect Node version =====
$nodeVersionFull = (& node -v 2>$null)
if (-not $nodeVersionFull) {
    Write-Host "❌ Error: Node.js is not installed or not in PATH" -ForegroundColor Red
    exit 1
}
$nodeVersion = [int]($nodeVersionFull -replace '^v(\d+)\..*', '$1')
Write-Host "🔍 Detected Node.js version: $nodeVersion" -ForegroundColor Cyan

if ($nodeVersion -lt 18) {
    Write-Host "❌ Error: Node.js 18 or higher is required" -ForegroundColor Red
    Write-Host "   Current version: $nodeVersionFull"
    exit 1
}

# Set Vite version based on Node version
if ($nodeVersion -ge 20) {
    $viteVersion = 'latest'
    Write-Host "✅ Using Vite latest (Node 20+)" -ForegroundColor Green
} else {
    $viteVersion = '5.4.11'
    Write-Host "✅ Using Vite $viteVersion (Node 18 compatible)" -ForegroundColor Green
}

# ===== Check if pnpm is installed =====
$pnpmExists = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpmExists) {
    Write-Host "📦 pnpm not found. Installing pnpm..." -ForegroundColor Yellow
    & npm install -g pnpm
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install pnpm" -ForegroundColor Red
        exit 1
    }
}

$componentsTarball = Join-Path $ScriptDir 'shadcn-components.tar.gz'
if (-not (Test-Path $componentsTarball)) {
    Write-Host "❌ Error: shadcn-components.tar.gz not found in script directory" -ForegroundColor Red
    Write-Host "   Expected location: $componentsTarball"
    exit 1
}

Write-Host "🚀 Creating new React + Vite project: $ProjectName" -ForegroundColor Cyan

# ===== Create Vite project =====
& pnpm create vite $ProjectName --template react-ts
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create Vite project" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectName

# ===== Clean up Vite template =====
Write-Host "🧹 Cleaning up Vite template..."
$indexHtml = Get-Content 'index.html' -Encoding UTF8
$indexHtml = $indexHtml | Where-Object { $_ -notmatch '<link rel="icon".*vite\.svg' }
$indexHtml = $indexHtml -replace '<title>.*?</title>', "<title>$ProjectName</title>"
Set-Content -Path 'index.html' -Value $indexHtml -Encoding UTF8

# ===== Install base dependencies =====
Write-Host "📦 Installing base dependencies..." -ForegroundColor Cyan
& pnpm install
if ($LASTEXITCODE -ne 0) { Write-Host "❌ pnpm install failed" -ForegroundColor Red; exit 1 }

# Pin Vite version for Node 18
if ($nodeVersion -lt 20) {
    Write-Host "📌 Pinning Vite to $viteVersion for Node 18 compatibility..."
    & pnpm add -D "vite@$viteVersion"
}

# ===== Install Tailwind CSS and dependencies =====
Write-Host "📦 Installing Tailwind CSS and dependencies..." -ForegroundColor Cyan
& pnpm install -D tailwindcss@3.4.1 postcss autoprefixer '@types/node' tailwindcss-animate
& pnpm install class-variance-authority clsx tailwind-merge lucide-react next-themes

# ===== Create PostCSS config =====
Write-Host "⚙️  Creating Tailwind and PostCSS configuration..."
@"
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"@ | Set-Content -Path 'postcss.config.js' -Encoding UTF8

# ===== Create Tailwind config =====
Write-Host "📝 Configuring Tailwind with shadcn theme..."
@"
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
"@ | Set-Content -Path 'tailwind.config.js' -Encoding UTF8

# ===== Add Tailwind directives and CSS variables =====
Write-Host "🎨 Adding Tailwind directives and CSS variables..."
@"
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 0 0% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 0 0% 3.9%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --muted: 0 0% 96.1%;
    --muted-foreground: 0 0% 45.1%;
    --accent: 0 0% 96.1%;
    --accent-foreground: 0 0% 9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 89.8%;
    --input: 0 0% 89.8%;
    --ring: 0 0% 3.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 0 0% 3.9%;
    --foreground: 0 0% 98%;
    --card: 0 0% 3.9%;
    --card-foreground: 0 0% 98%;
    --popover: 0 0% 3.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 0 0% 9%;
    --secondary: 0 0% 14.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 0 0% 14.9%;
    --muted-foreground: 0 0% 63.9%;
    --accent: 0 0% 14.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 14.9%;
    --input: 0 0% 14.9%;
    --ring: 0 0% 83.1%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
"@ | Set-Content -Path 'src/index.css' -Encoding UTF8

# ===== Add path aliases to tsconfig.json =====
Write-Host "🔧 Adding path aliases to tsconfig.json..."
& node -e @"
const fs = require('fs');
const config = JSON.parse(fs.readFileSync('tsconfig.json', 'utf8'));
config.compilerOptions = config.compilerOptions || {};
config.compilerOptions.baseUrl = '.';
config.compilerOptions.paths = { '@/*': ['./src/*'] };
fs.writeFileSync('tsconfig.json', JSON.stringify(config, null, 2));
"@

# ===== Add path aliases to tsconfig.app.json =====
Write-Host "🔧 Adding path aliases to tsconfig.app.json..."
& node -e @"
const fs = require('fs');
const p = 'tsconfig.app.json';
const content = fs.readFileSync(p, 'utf8');
const lines = content.split('\n').filter(line => !line.trim().startsWith('//'));
const jsonContent = lines.join('\n');
const config = JSON.parse(jsonContent.replace(/\/\*[\s\S]*?\*\//g, '').replace(/,(\s*[}\]])/g, '$1'));
config.compilerOptions = config.compilerOptions || {};
config.compilerOptions.baseUrl = '.';
config.compilerOptions.paths = { '@/*': ['./src/*'] };
fs.writeFileSync(p, JSON.stringify(config, null, 2));
"@

# ===== Update vite.config.ts =====
Write-Host "⚙️  Updating Vite configuration..."
@"
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
"@ | Set-Content -Path 'vite.config.ts' -Encoding UTF8

# ===== Install shadcn/ui dependencies =====
Write-Host "📦 Installing shadcn/ui dependencies..." -ForegroundColor Cyan
& pnpm install `
    '@radix-ui/react-accordion' '@radix-ui/react-aspect-ratio' '@radix-ui/react-avatar' `
    '@radix-ui/react-checkbox' '@radix-ui/react-collapsible' '@radix-ui/react-context-menu' `
    '@radix-ui/react-dialog' '@radix-ui/react-dropdown-menu' '@radix-ui/react-hover-card' `
    '@radix-ui/react-label' '@radix-ui/react-menubar' '@radix-ui/react-navigation-menu' `
    '@radix-ui/react-popover' '@radix-ui/react-progress' '@radix-ui/react-radio-group' `
    '@radix-ui/react-scroll-area' '@radix-ui/react-select' '@radix-ui/react-separator' `
    '@radix-ui/react-slider' '@radix-ui/react-slot' '@radix-ui/react-switch' `
    '@radix-ui/react-tabs' '@radix-ui/react-toast' '@radix-ui/react-toggle' `
    '@radix-ui/react-toggle-group' '@radix-ui/react-tooltip'

& pnpm install sonner cmdk vaul embla-carousel-react react-day-picker react-resizable-panels date-fns react-hook-form '@hookform/resolvers' zod

# ===== Extract shadcn components from tarball =====
Write-Host "📦 Extracting shadcn/ui components..." -ForegroundColor Cyan
# Windows 10+ has built-in tar
& tar -xzf $componentsTarball -C src/
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to extract components tarball" -ForegroundColor Red
    exit 1
}

# ===== Create components.json =====
Write-Host "📝 Creating components.json config..."
@"
{
  "`$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
"@ | Set-Content -Path 'components.json' -Encoding UTF8

Write-Host ""
Write-Host "✅ Setup complete! You can now use Tailwind CSS and shadcn/ui in your project." -ForegroundColor Green
Write-Host ""
Write-Host "📦 Included components (40+ total):" -ForegroundColor Cyan
Write-Host "  - accordion, alert, aspect-ratio, avatar, badge, breadcrumb"
Write-Host "  - button, calendar, card, carousel, checkbox, collapsible"
Write-Host "  - command, context-menu, dialog, drawer, dropdown-menu"
Write-Host "  - form, hover-card, input, label, menubar, navigation-menu"
Write-Host "  - popover, progress, radio-group, resizable, scroll-area"
Write-Host "  - select, separator, sheet, skeleton, slider, sonner"
Write-Host "  - switch, table, tabs, textarea, toast, toggle, toggle-group, tooltip"
Write-Host ""
Write-Host "To start developing:" -ForegroundColor Cyan
Write-Host "  cd $ProjectName"
Write-Host "  pnpm dev"
Write-Host ""
Write-Host "📚 Import components like:" -ForegroundColor Cyan
Write-Host "  import { Button } from '@/components/ui/button'"
Write-Host "  import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'"
Write-Host "  import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'"
