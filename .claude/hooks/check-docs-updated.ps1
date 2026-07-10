$ErrorActionPreference = 'SilentlyContinue'

$changed = git -c core.quotepath=false status --porcelain --untracked-files=all
if (-not $changed) {
    exit 0
}

$paths = $changed | ForEach-Object {
    $_.Substring(3).Trim().Trim('"') -replace ' -> .*$', ''
}

$sourcePattern = '^(backend/app/|backend/alembic/versions/|frontend/src/)'
$docsPattern = '^(docs/requirements\.md$|docs/詳細設計書/|CONTEXT\.md$|docs/adr/|docs/課題管理書\.md$)'

$sourceChanged = $paths | Where-Object { $_ -match $sourcePattern }
$docsChanged = $paths | Where-Object { $_ -match $docsPattern }

if ($sourceChanged -and -not $docsChanged) {
    $fileList = ($sourceChanged | Select-Object -First 8) -join ', '
    $message = "[doc-check] backend/app・backend/alembic・frontend/src に変更がありますが、docs/requirements.md / docs/詳細設計書 / CONTEXT.md / docs/adr / docs/課題管理書.md はいずれも変更されていません。該当する場合はドキュメントも更新してください(仕様に影響しない変更であれば無視して構いません)。変更ファイル: $fileList"
    $obj = [ordered]@{ systemMessage = $message }
    $obj | ConvertTo-Json -Compress
}

exit 0
