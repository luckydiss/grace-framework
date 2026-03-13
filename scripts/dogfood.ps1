param(
    [string]$RepoRoot = ".",
    [string]$Scope = "examples/basic",
    [string]$File = "examples/basic/pricing.py",
    [string]$Anchor = "billing.pricing.apply_discount",
    [string]$Replacement = "examples/basic/apply_discount.replacement.pyfrag",
    [string]$Plan = "examples/basic/apply_discount.plan.json",
    [switch]$SkipInstall,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

function Invoke-Step {
    param(
        [string]$Label,
        [string[]]$Command
    )

    Write-Host "==> $Label"
    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Label"
    }
}

if (-not $SkipInstall) {
    Invoke-Step "Install editable package" @("python", "-m", "pip", "install", "-e", ".")
}

if (-not $SkipTests) {
    Invoke-Step "Run test suite" @("python", "-m", "pytest", "-q")
}

Invoke-Step "CLI help" @("python", "-m", "grace.cli", "--help")
Invoke-Step "Parse scope" @("python", "-m", "grace.cli", "parse", $Scope, "--json")
Invoke-Step "Validate scope" @("python", "-m", "grace.cli", "validate", $Scope, "--json")
Invoke-Step "Lint scope" @("python", "-m", "grace.cli", "lint", $Scope, "--json")
Invoke-Step "Build map" @("python", "-m", "grace.cli", "map", $Scope, "--json")
Invoke-Step "Dry-run patch" @("python", "-m", "grace.cli", "patch", $File, $Anchor, $Replacement, "--dry-run", "--json")
Invoke-Step "Dry-run apply-plan" @("python", "-m", "grace.cli", "apply-plan", $Plan, "--dry-run", "--json")

Write-Host "Dogfood run completed."
