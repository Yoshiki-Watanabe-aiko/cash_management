import fs from 'node:fs'

function parseEnvFile(filePath: string): Record<string, string> {
  const content = fs.readFileSync(filePath, 'utf-8')
  const result: Record<string, string> = {}
  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const eqIndex = line.indexOf('=')
    if (eqIndex === -1) continue
    result[line.slice(0, eqIndex).trim()] = line.slice(eqIndex + 1).trim()
  }
  return result
}

/**
 * 本番用.envのDATABASE_URLからデータベース名だけをcash_management_testに
 * 差し替えたE2Eテスト専用の接続文字列を返す(認証情報は.envのものを再利用)。
 */
export function getTestDatabaseUrl(rootEnvPath: string): string {
  const env = parseEnvFile(rootEnvPath)
  const databaseUrl = env.DATABASE_URL
  if (!databaseUrl) {
    throw new Error(`${rootEnvPath} に DATABASE_URL が設定されていません`)
  }
  return databaseUrl.replace(/\/[^/]+$/, '/cash_management_test')
}
