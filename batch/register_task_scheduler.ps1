<#
.SYNOPSIS
    日次バッチ(統合資産・経費管理システム)をWindowsタスクスケジューラへ登録する。

.DESCRIPTION
    要件定義書2章・ADR 0008の方針に沿って以下を設定する:
      - 毎日深夜2時に実行
      - スケジュールされた時刻を逃した場合はできるだけ早く実行する(StartWhenAvailable)
      - スリープを解除してタスクを実行する(WakeToRun)
      - 保険としてログオン時・システム起動時トリガーも追加する

.NOTES
    管理者権限のPowerShellで実行すること。
    実行方法: powershell -ExecutionPolicy Bypass -File .\register_task_scheduler.ps1
#>

param(
    [string]$TaskName = "CashManagementDailyImport",
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$BackendDir = Join-Path $RepoRoot "backend"
$LogFile = Join-Path $RepoRoot "logs\task_scheduler.log"

if (-not (Test-Path $BackendDir)) {
    throw "backendディレクトリが見つかりません: $BackendDir"
}

$uvPath = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uvPath) {
    throw "uvコマンドが見つかりません。PATHを確認するか、-UvPathパラメータで明示的に指定してください。"
}

$actionArgument = "/c `"cd /d `"$BackendDir`" && `"$uvPath`" run python -m app.cli.run_daily_import >> `"$LogFile`" 2>&1`""
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $actionArgument

$dailyTrigger = New-ScheduledTaskTrigger -Daily -At 2:00am
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
$startupTrigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($dailyTrigger, $logonTrigger, $startupTrigger) `
    -Settings $settings `
    -Description "統合資産・経費管理システム 日次取込バッチ(CSV/カードメール/バックアップ)" `
    -RunLevel Limited `
    -Force

Write-Host "タスク '$TaskName' を登録しました。ログ出力先: $LogFile"
Write-Host "動作確認: Start-ScheduledTask -TaskName '$TaskName'"
