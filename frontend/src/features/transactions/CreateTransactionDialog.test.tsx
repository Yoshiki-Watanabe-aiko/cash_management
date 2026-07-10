import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CreateTransactionDialog } from './CreateTransactionDialog'

const useCreateTransactionMock = vi.fn()

vi.mock('./queries', () => ({
  useCreateTransaction: () => useCreateTransactionMock(),
}))

vi.mock('@/features/reference/queries', () => ({
  useAccounts: () => ({ data: [{ id: 1, account_name: '楽天銀行 個人' }] }),
  useCategories: () => ({ data: [{ id: 1, category_name: '食費' }] }),
}))

describe('CreateTransactionDialog', () => {
  it('creates an expense transaction with a negative amount by default', async () => {
    const mutate = vi.fn()
    useCreateTransactionMock.mockReturnValue({ mutate, isPending: false })
    const user = userEvent.setup()

    render(<CreateTransactionDialog />)
    await user.click(screen.getByRole('button', { name: '取引を追加' }))
    await user.type(screen.getByLabelText('摘要'), '現金(財布)払い')
    await user.type(screen.getByLabelText('金額'), '1000')
    await user.click(screen.getByRole('button', { name: '登録' }))

    expect(mutate).toHaveBeenCalledWith(
      {
        account_id: null,
        transaction_date: expect.any(String),
        amount: -1000,
        description: '現金(財布)払い',
        category_id: null,
        business_ratio: 100,
      },
      expect.anything(),
    )
  })

  it('shows a validation error and does not submit when description is empty', async () => {
    const mutate = vi.fn()
    useCreateTransactionMock.mockReturnValue({ mutate, isPending: false })
    const user = userEvent.setup()

    render(<CreateTransactionDialog />)
    await user.click(screen.getByRole('button', { name: '取引を追加' }))
    await user.type(screen.getByLabelText('金額'), '1000')
    await user.click(screen.getByRole('button', { name: '登録' }))

    expect(screen.getByText('摘要を入力してください')).toBeInTheDocument()
    expect(mutate).not.toHaveBeenCalled()
  })

  it('shows a validation error and does not submit when amount is zero or empty', async () => {
    const mutate = vi.fn()
    useCreateTransactionMock.mockReturnValue({ mutate, isPending: false })
    const user = userEvent.setup()

    render(<CreateTransactionDialog />)
    await user.click(screen.getByRole('button', { name: '取引を追加' }))
    await user.type(screen.getByLabelText('摘要'), '摘要のみ入力')
    await user.click(screen.getByRole('button', { name: '登録' }))

    expect(screen.getByText('金額には0より大きい数値を入力してください')).toBeInTheDocument()
    expect(mutate).not.toHaveBeenCalled()
  })

  it('shows the API error message when creation fails', async () => {
    const mutate = vi.fn((_payload, { onError }: { onError: (error: unknown) => void }) => {
      onError(new Error('unexpected'))
    })
    useCreateTransactionMock.mockReturnValue({ mutate, isPending: false })
    const user = userEvent.setup()

    render(<CreateTransactionDialog />)
    await user.click(screen.getByRole('button', { name: '取引を追加' }))
    await user.type(screen.getByLabelText('摘要'), '登録失敗テスト')
    await user.type(screen.getByLabelText('金額'), '500')
    await user.click(screen.getByRole('button', { name: '登録' }))

    expect(screen.getByText('登録に失敗しました')).toBeInTheDocument()
  })
})
