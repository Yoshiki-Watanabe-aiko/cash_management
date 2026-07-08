import { expect, test } from '@playwright/test'

test.describe('振替の手動紐づけ', () => {
  test('出金側・入金側を選択して紐づけると、フォームがリセットされ候補から消える', async ({ page }) => {
    await page.goto('/transactions')
    await page.getByRole('tab', { name: '振替の手動紐づけ' }).click()

    const fromSelect = page.getByLabel('出金側')
    const toSelect = page.getByLabel('入金側')
    const linkButton = page.getByRole('button', { name: '紐づける' })

    await expect(fromSelect).toBeVisible()
    await expect(toSelect).toBeVisible()
    await expect(linkButton).toBeDisabled()

    await fromSelect.click()
    await page.getByRole('option', { name: /振替出金/ }).click()

    await toSelect.click()
    await page.getByRole('option', { name: /振替入金/ }).click()

    await expect(linkButton).toBeEnabled()
    await linkButton.click()

    // 紐づけ成功後はフォームが未選択状態に戻り、紐づけた取引は候補から消える
    await expect(fromSelect).toHaveText('出金取引を選択')
    await fromSelect.click()
    await expect(page.getByRole('option', { name: /振替出金/ })).toHaveCount(0)
  })
})
