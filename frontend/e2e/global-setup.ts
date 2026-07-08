import { execSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { getTestDatabaseUrl } from './env'

const THIS_DIR = path.dirname(fileURLToPath(import.meta.url))

/**
 * E2Eテスト専用データベース(cash_management_test)のスキーマを破棄・再作成し、
 * 決定論的なフィクスチャデータを投入する(backend/app/db/e2e_seed.py)。
 * 対象データベースは本番用cash_managementとは別物であり、ここでのリセットが
 * ユーザー本人の実際の資産・取引データに影響することはない。
 */
export default function globalSetup(): void {
  const rootDir = path.resolve(THIS_DIR, '../..')
  const backendDir = path.join(rootDir, 'backend')
  const testDatabaseUrl = getTestDatabaseUrl(path.join(rootDir, '.env'))

  execSync('uv run python -m app.db.e2e_seed', {
    cwd: backendDir,
    env: { ...process.env, DATABASE_URL: testDatabaseUrl },
    stdio: 'inherit',
  })
}
