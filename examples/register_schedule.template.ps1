#!/usr/bin/env pwsh
# Template: register workspace-metabolism scheduled tasks on Windows.
#
# Replace the {{PLACEHOLDERS}} before running:
#   {{WM_CMD}}     - how to invoke the tool, e.g. C:\Python312\python.exe -m workspace_metabolism  (or: wm)
#   {{ROOT}}       - absolute path of the workspace to govern
#   {{REGISTRY}}   - absolute path of the policy registry (JSON)
#   {{STATE_DIR}}  - absolute path of the state directory
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File register_schedule.template.ps1
#   powershell -ExecutionPolicy Bypass -File register_schedule.template.ps1 -Unregister

param([switch]$Unregister)

$ErrorActionPreference = "Stop"
$wm = "{{WM_CMD}}"
$root = "{{ROOT}}"
$registry = "{{REGISTRY}}"
$stateDir = "{{STATE_DIR}}"
$common = "--root `"$root`" --registry `"$registry`" --state-dir `"$stateDir`""

$tasks = @(
    @{ Name = "ws-metabolism-audit"; Arg = "audit --auto"; Schedule = @("/SC", "DAILY", "/ST", "20:30"); Desc = "daily read-only audit" },
    @{ Name = "ws-metabolism-clean"; Arg = "clean --grades G4 --yes --auto"; Schedule = @("/SC", "WEEKLY", "/D", "SAT", "/ST", "10:00"); Desc = "weekly G4 auto-clean (recyclable)" },
    @{ Name = "ws-metabolism-purge"; Arg = "purge --older-than 30 --yes --auto"; Schedule = @("/SC", "MONTHLY", "/D", "1", "/ST", "10:30"); Desc = "monthly purge of expired recycle batches" }
)

foreach ($t in $tasks) {
    if ($Unregister) {
        & schtasks.exe /Delete /F /TN $t.Name 2>$null | Out-Null
        Write-Host "unregistered: $($t.Name)"
        continue
    }
    $cmdLine = "$wm $($t.Arg) $common"
    & schtasks.exe /Create /F /TN $t.Name /TR $cmdLine @($t.Schedule) /RL LIMITED /IT
    if ($LASTEXITCODE -eq 0) {
        Write-Host "registered: $($t.Name) ($($t.Desc))" -ForegroundColor Green
    } else {
        Write-Host "registration failed: $($t.Name) (exit $LASTEXITCODE)" -ForegroundColor Red
    }
}
