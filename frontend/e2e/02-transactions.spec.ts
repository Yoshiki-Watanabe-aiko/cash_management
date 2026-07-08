import { expect, test } from '@playwright/test'

test.describe('取引管理', () => {
  test('シードした取引が一覧に表示され、未分類フィルタと再分類ボタンが機能する', async ({ page }) => {
    await page.goto('/transactions')

    await expect(page.getByText('取引先接待')).toBeVisible()
    await expect(page.getByText('スーパーで食料品購入')).toBeVisible()
    await expect(page.getByText('給与振込')).toBeVisible()

    await page.getByLabel('未分類のみ').check()
    await expect(page.getByText('スーパーで食料品購入')).toBeVisible()
    await expect(page.getByText('取引先接待')).toHaveCount(0)

    await page.getByRole('button', { name: /未分類の取引にルールを再適用/ }).click()

    // m_category_rules("スーパー"→食費)により再分類されるため、未分類フィルタ適用中は表示されなくなる
    await expect(page.getByText('スーパーで食料品購入')).toHaveCount(0)

    await page.getByLabel('未分類のみ').uncheck()
    await expect(page.getByText('スーパーで食料品購入')).toBeVisible()
  })
})
