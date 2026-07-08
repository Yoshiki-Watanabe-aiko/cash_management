import { expect, test } from '@playwright/test'

test.describe('ダッシュボード', () => {
  test('4つのウィジェットがシードデータで表示される', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText('純資産の推移')).toBeVisible()
    await expect(page.getByText('資産スナップショットがまだありません')).toHaveCount(0)

    await expect(page.getByText('今月の事業経費の進捗')).toBeVisible()
    await expect(page.getByText('接待交際費').first()).toBeVisible()
    await expect(page.getByText(/予算超過/)).toHaveCount(0)

    await expect(page.getByText(/個人口座のキャッシュフロー/)).toBeVisible()
    await expect(page.getByText('収入').first()).toBeVisible()
    await expect(page.getByText('支出').first()).toBeVisible()

    await expect(page.getByText('カテゴリ別の支出')).toBeVisible()
    await expect(page.getByText('今月の支出はまだありません')).toHaveCount(0)
  })
})
