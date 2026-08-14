<#
.SYNOPSIS
  Install the Git-backed AI knowledge harness for user-level agent runtimes.

.DESCRIPTION
  Idempotently installs command routing and canonical instruction surfaces while
  leaving the repository checkout as the only knowledge source of truth.

.PARAMETER Check
  Report drift without writing. Returns 1 when a surface is missing or stale.

.PARAMETER Uninstall
  Remove managed surfaces, environment variables, and the PATH entry.

.PARAMETER SkipFutureTools
  Do not create configuration directories for agent runtimes not yet installed.
#>
[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$Uninstall,
    [switch]$SkipFutureTools
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $RepoRoot 'bin'
$Surfaces = Join-Path $RepoRoot 'surfaces'
$NewBegin = '<!-- BEGIN ai-knowledge-harness -->'
$NewEnd = '<!-- END ai-knowledge-harness -->'
$LegacyBegin = '<!-- BEGIN ai-knowledge-base'
$LegacyEnd = '<!-- END ai-knowledge-base -->'
$script:Drift = 0
$script:Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Say([string]$Message, [string]$Color = 'Gray') {
    Write-Host $Message -ForegroundColor $Color
}

function Good([string]$Message) {
    Say "  ok      $Message" 'Green'
}

function Changed([string]$Message) {
    Say "  wrote   $Message" 'Cyan'
}

function Missing([string]$Message) {
    Say "  MISSING $Message" 'Red'
    $script:Drift++
}

function Stale([string]$Message) {
    Say "  STALE   $Message" 'Yellow'
    $script:Drift++
}

function Skipped([string]$Message) {
    Say "  skip    $Message" 'DarkGray'
}

function FileHash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Write-Utf8NoBom([string]$Path, [string]$Value) {
    [System.IO.File]::WriteAllText($Path, $Value, $script:Utf8NoBom)
}

function Find-Python {
    $candidates = @(
        [pscustomobject]@{ Exe = 'py'; Prefix = @('-3') },
        [pscustomobject]@{ Exe = 'python3'; Prefix = @() },
        [pscustomobject]@{ Exe = 'python'; Prefix = @() }
    )
    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Exe -ErrorAction SilentlyContinue)) {
            continue
        }
        & $candidate.Exe @($candidate.Prefix) -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }
    }
    throw 'Python 3.9 or newer is required but was not found on PATH.'
}

function Sync-File([string]$Source, [string]$Destination) {
    $Label = $Destination.Replace($HOME, '~')
    $exists = Test-Path -LiteralPath $Destination -PathType Leaf
    if ($Uninstall) {
        if (-not $exists) {
            Skipped "$Label (absent)"
            return
        }
        if ((FileHash $Source) -ne (FileHash $Destination)) {
            Stale "$Label (user-modified; preserved)"
            return
        }
        Remove-Item -LiteralPath $Destination -Force
        Changed "removed $Label"
        return
    }

    $same = $exists -and (FileHash $Source) -eq (FileHash $Destination)
    if ($Check) {
        if (-not $exists) {
            Missing $Label
        }
        elseif (-not $same) {
            Stale $Label
        }
        else {
            Good $Label
        }
        return
    }
    if ($same) {
        Good $Label
        return
    }
    $directory = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    if ($exists -and -not (Test-Path -LiteralPath "$Destination.aikb-bak")) {
        Copy-Item -LiteralPath $Destination -Destination "$Destination.aikb-bak"
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    Changed $Label
}

function Remove-ManagedBlocks([string]$Text) {
    $newPattern = '(?s)' + [regex]::Escape($NewBegin) + '.*?' + [regex]::Escape($NewEnd) + '\r?\n?'
    $legacyPattern = '(?s)' + [regex]::Escape($LegacyBegin) + '.*?' + [regex]::Escape($LegacyEnd) + '\r?\n?'
    $withoutNew = [regex]::Replace($Text, $newPattern, '')
    return [regex]::Replace($withoutNew, $legacyPattern, '')
}

function Sync-Block([string]$BlockFile, [string]$Destination, [bool]$CreateDirectory) {
    $Label = $Destination.Replace($HOME, '~')
    $directory = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $directory)) {
        if ($Check -or $Uninstall -or -not $CreateDirectory) {
            Skipped "$Label (directory absent)"
            return
        }
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $existing = if (Test-Path -LiteralPath $Destination) {
        Get-Content -LiteralPath $Destination -Raw
    }
    else {
        ''
    }
    $block = (Get-Content -LiteralPath $BlockFile -Raw).TrimEnd() + "`r`n"
    $stripped = (Remove-ManagedBlocks $existing).TrimEnd()
    $desired = if ($stripped) {
        $stripped + "`r`n`r`n" + $block
    }
    else {
        $block
    }
    $hasNew = $existing.Contains($NewBegin) -and $existing.Contains($NewEnd)

    if ($Uninstall) {
        if (-not $hasNew) {
            Skipped "$Label (managed block absent)"
            return
        }
        if ($stripped) {
            Write-Utf8NoBom $Destination ($stripped + "`r`n")
        }
        else {
            Remove-Item -LiteralPath $Destination -Force
        }
        Changed "removed block from $Label"
        return
    }
    if ($Check) {
        if (-not $hasNew) {
            Missing "$Label (managed block absent)"
        }
        elseif ($existing -ne $desired) {
            Stale $Label
        }
        else {
            Good $Label
        }
        return
    }
    if ($existing -eq $desired) {
        Good $Label
        return
    }
    if ($existing -and -not (Test-Path -LiteralPath "$Destination.aikb-bak")) {
        Copy-Item -LiteralPath $Destination -Destination "$Destination.aikb-bak"
    }
    Write-Utf8NoBom $Destination $desired
    Changed $Label
}

Say ''
Say "AI knowledge harness - repository: $RepoRoot" 'Cyan'
Say ("mode: " + $(if ($Check) { 'CHECK' } elseif ($Uninstall) { 'UNINSTALL' } else { 'INSTALL' })) 'Cyan'

if (-not $Uninstall) {
    $python = Find-Python
    Say ''
    Say '[0] repository validation'
    & $python.Exe @($python.Prefix) (Join-Path $BinDir 'aikb.py') --repo $RepoRoot validate --projection
    if ($LASTEXITCODE -ne 0) {
        throw 'Repository validation failed; installation stopped before changing user surfaces.'
    }
}

Say ''
Say '[1] environment'
$currentRepo = [Environment]::GetEnvironmentVariable('AI_KB_REPO', 'User')
$currentRoot = [Environment]::GetEnvironmentVariable('AI_KB_ROOT', 'User')
$currentPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not $currentPath) {
    $currentPath = ''
}
$pathEntries = @($currentPath -split ';' | Where-Object { $_ })
$onPath = @($pathEntries | Where-Object { $_.TrimEnd('\') -ieq $BinDir.TrimEnd('\') }).Count -gt 0

if ($Uninstall) {
    if ($currentRepo -eq $RepoRoot) {
        [Environment]::SetEnvironmentVariable('AI_KB_REPO', $null, 'User')
        Changed 'removed AI_KB_REPO'
    }
    if ($currentRoot -eq $RepoRoot) {
        [Environment]::SetEnvironmentVariable('AI_KB_ROOT', $null, 'User')
        Changed 'removed AI_KB_ROOT compatibility variable'
    }
    if ($onPath) {
        $newPath = @($pathEntries | Where-Object { $_.TrimEnd('\') -ine $BinDir.TrimEnd('\') }) -join ';'
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        Changed 'removed harness bin from user PATH'
    }
}
elseif ($Check) {
    if ($currentRepo -eq $RepoRoot) { Good 'AI_KB_REPO' } else { Missing "AI_KB_REPO (is '$currentRepo')" }
    if ($currentRoot -eq $RepoRoot) { Good 'AI_KB_ROOT compatibility variable' } else { Missing "AI_KB_ROOT (is '$currentRoot')" }
    if ($onPath) { Good 'user PATH contains harness bin' } else { Missing "user PATH missing $BinDir" }
}
else {
    if ($currentRepo -ne $RepoRoot) {
        [Environment]::SetEnvironmentVariable('AI_KB_REPO', $RepoRoot, 'User')
        Changed "AI_KB_REPO=$RepoRoot"
    }
    else { Good 'AI_KB_REPO' }
    if ($currentRoot -ne $RepoRoot) {
        [Environment]::SetEnvironmentVariable('AI_KB_ROOT', $RepoRoot, 'User')
        Changed "AI_KB_ROOT=$RepoRoot"
    }
    else { Good 'AI_KB_ROOT compatibility variable' }
    if (-not $onPath) {
        $newPath = (@($pathEntries) + $BinDir) -join ';'
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        Changed "user PATH += $BinDir"
    }
    else { Good 'user PATH' }
    $env:AI_KB_REPO = $RepoRoot
    $env:AI_KB_ROOT = $RepoRoot
    if ($env:Path -notlike "*$BinDir*") {
        $env:Path = $env:Path.TrimEnd(';') + ';' + $BinDir
    }
}

Say ''
Say '[2] VS Code global instructions'
$vscodeSource = Join-Path $Surfaces 'vscode\ai-knowledge-base.instructions.md'
$profiles = @()
if (Test-Path -LiteralPath $env:APPDATA) {
    $profiles = @(Get-ChildItem -LiteralPath $env:APPDATA -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('Code', 'Code - Insiders', 'Code - Exploration', 'VSCodium', 'Cursor', 'Windsurf') })
}
if (-not $profiles) {
    Skipped 'no supported VS Code profile found'
}
foreach ($profile in $profiles) {
    Sync-File $vscodeSource (Join-Path $profile.FullName 'User\prompts\ai-knowledge-base.instructions.md')
}

Say ''
Say '[3] user-level skills'
$skillSource = Join-Path $Surfaces 'skill\SKILL.md'
Sync-File $skillSource (Join-Path $HOME '.copilot\skills\ai-knowledge-base\SKILL.md')
Sync-File $skillSource (Join-Path $HOME '.agents\skills\ai-knowledge-base\SKILL.md')

Say ''
Say '[4] AGENTS.md-compatible managed blocks'
$blockSource = Join-Path $Surfaces 'agents\AGENTS-block.md'
$createFuture = -not $SkipFutureTools
Sync-Block $blockSource (Join-Path $HOME 'AGENTS.md') $true
Sync-Block $blockSource (Join-Path $HOME '.codex\AGENTS.md') $createFuture
Sync-Block $blockSource (Join-Path $HOME '.claude\CLAUDE.md') $createFuture
Sync-Block $blockSource (Join-Path $HOME '.gemini\GEMINI.md') $createFuture

Say ''
if ($Check) {
    if ($script:Drift -eq 0) {
        Say 'in sync - repository and installed surfaces are current.' 'Green'
        exit 0
    }
    Say "$($script:Drift) surface(s) missing or stale." 'Yellow'
    exit 1
}
if ($Uninstall) {
    Say 'done - managed knowledge surfaces were removed.' 'Green'
}
else {
    Say 'done - open a new terminal, then run: aikb check' 'Green'
}
