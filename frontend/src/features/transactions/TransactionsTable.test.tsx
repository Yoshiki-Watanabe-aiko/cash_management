import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TransactionsTable } from './TransactionsTable'
import type { Transaction } from '@/api/types'
import type { TransactionFilters } from './queries'

const mutateMock = vi.fn()

vi.mock('@/features/reference/queries', () => ({
  useAccounts: () => ({
    data: [
      {
        id: 1,
        account_name: '楽天銀行 個人',
        account_type: 'bank',
        is_business: false,
        is_active: true,
        tracks_balance: true,
      },
    ],
  }),
  useCategories: () => ({ data: [{ id: 10, category_name: '食費' }] }),
}))

vi.mock('./queries', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./queries')>()
  return {
    ...actual,
    useUpdateTransaction: () => ({ mutate: mutateMock, isPending: false }),
  }
})

function makeTransaction(overrides: Partial<Transaction>): Transaction {
  return {
    id: 1,
    account_id: 1,
    transaction_date: '2026-07-01',
    amount: '-1000',
    description: 'テスト取引',
    category_id: null,
    business_ratio: '0',
    source_type: 'manual',
    is_transferred: false,
    ...overrides,
  }
}

const baseFilters: TransactionFilters = { page: 1, pageSize: 20 }

describe('TransactionsTable', () => {
  beforeEach(() => {
    mutateMock.mockReset()
  })

  it('shows an error message when fetching fails', () => {
    render(
      <TransactionsTable
        transactions={[]}
        total={0}
        isLoading={false}
        isError
        filters={baseFilters}
        onFiltersChange={vi.fn()}
      />,
    )
    expect(screen.getByText('取引の取得に失敗しました')).toBeInTheDocument()
  })

  it('shows an empty state when there are no matching transactions', () => {
    render(
      <TransactionsTable
        transactions={[]}
        total={0}
        isLoading={false}
        isError={false}
        filters={baseFilters}
        onFiltersChange={vi.fn()}
      />,
    )
    expect(screen.getByText('該当する取引がありません')).toBeInTheDocument()
  })

  it('renders transaction rows with formatted date, account name, description, and amount', () => {
    render(
      <TransactionsTable
        transactions={[
          makeTransaction({ id: 1, amount: '-1500', transaction_date: '2026-07-01', description: 'コンビニ' }),
        ]}
        total={1}
        isLoading={false}
        isError={false}
        filters={baseFilters}
        onFiltersChange={vi.fn()}
      />,
    )
    expect(screen.getByText('2026/07/01')).toBeInTheDocument()
    expect(screen.getByText('楽天銀行 個人')).toBeInTheDocument()
    expect(screen.getByText('コンビニ')).toBeInTheDocument()
    expect(screen.getByText('-￥1,500')).toBeInTheDocument()
  })

  it('disables prev/next buttons when there is only one page', () => {
    render(
      <TransactionsTable
        transactions={[makeTransaction({ id: 1 })]}
        total={1}
        isLoading={false}
        isError={false}
        filters={{ page: 1, pageSize: 20 }}
        onFiltersChange={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /前へ/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /次へ/ })).toBeDisabled()
  })

  it('calls onFiltersChange with the next page when the next button is clicked', async () => {
    const onFiltersChange = vi.fn()
    const user = userEvent.setup()
    render(
      <TransactionsTable
        transactions={Array.from({ length: 20 }, (_, i) => makeTransaction({ id: i + 1 }))}
        total={40}
        isLoading={false}
        isError={false}
        filters={{ page: 1, pageSize: 20 }}
        onFiltersChange={onFiltersChange}
      />,
    )
    await user.click(screen.getByRole('button', { name: /次へ/ }))
    expect(onFiltersChange).toHaveBeenCalledWith({ page: 2, pageSize: 20 })
  })

  it('commits a business-ratio edit to the transaction under that row, not a different transaction occupying the same row position after a page change', () => {
    // Phase 7で修正した「ページ送り・再フェッチ時に別取引へ誤って更新が飛ぶ」不具合の回帰テスト。
    const { rerender } = render(
      <TransactionsTable
        transactions={[
          makeTransaction({ id: 5, business_ratio: '10' }),
          makeTransaction({ id: 6, business_ratio: '20' }),
        ]}
        total={2}
        isLoading={false}
        isError={false}
        filters={baseFilters}
        onFiltersChange={vi.fn()}
      />,
    )

    const firstRenderInputs = screen.getAllByLabelText('事業按分率')
    fireEvent.change(firstRenderInputs[0], { target: { value: '55' } })
    fireEvent.blur(firstRenderInputs[0])

    expect(mutateMock).toHaveBeenCalledWith({ id: 5, update: { business_ratio: 55 } }, expect.anything())

    mutateMock.mockReset()

    rerender(
      <TransactionsTable
        transactions={[
          makeTransaction({ id: 7, business_ratio: '30' }),
          makeTransaction({ id: 8, business_ratio: '40' }),
        ]}
        total={2}
        isLoading={false}
        isError={false}
        filters={baseFilters}
        onFiltersChange={vi.fn()}
      />,
    )

    const secondRenderInputs = screen.getAllByLabelText('事業按分率')
    fireEvent.change(secondRenderInputs[0], { target: { value: '77' } })
    fireEvent.blur(secondRenderInputs[0])

    expect(mutateMock).toHaveBeenCalledWith({ id: 7, update: { business_ratio: 77 } }, expect.anything())
  })
})
