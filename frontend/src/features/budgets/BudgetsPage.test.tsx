import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BudgetsPage } from './BudgetsPage'

const useBudgetsListMock = vi.fn()
const useCreateBudgetMock = vi.fn()
const useUpdateBudgetMock = vi.fn()
const useDeleteBudgetMock = vi.fn()

vi.mock('./queries', () => ({
  useBudgetsList: (...args: unknown[]) => useBudgetsListMock(...args),
  useCreateBudget: () => useCreateBudgetMock(),
  useUpdateBudget: () => useUpdateBudgetMock(),
  useDeleteBudget: () => useDeleteBudgetMock(),
}))

vi.mock('@/features/reference/queries', () => ({
  useCategories: () => ({ data: [{ id: 1, category_name: '食費' }] }),
}))

describe('BudgetsPage', () => {
  it('shows an error message when budgets fail to load', () => {
    useBudgetsListMock.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    useCreateBudgetMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useDeleteBudgetMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<BudgetsPage />)

    expect(screen.getByText('予算の取得に失敗しました')).toBeInTheDocument()
  })

  it('shows an empty state when no budgets are configured for the month', () => {
    useBudgetsListMock.mockReturnValue({ data: [], isLoading: false, isError: false })
    useCreateBudgetMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useDeleteBudgetMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<BudgetsPage />)

    expect(screen.getByText('この年月の予算はまだ設定されていません')).toBeInTheDocument()
  })

  it('renders a budget row with category name and business/personal label', () => {
    useBudgetsListMock.mockReturnValue({
      data: [{ id: 1, category_id: 1, year_month: '2026-07', is_business: true, budget_amount: '10000' }],
      isLoading: false,
      isError: false,
    })
    useCreateBudgetMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useDeleteBudgetMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<BudgetsPage />)

    expect(screen.getByText('食費')).toBeInTheDocument()
    expect(screen.getByText('事業')).toBeInTheDocument()
    expect(screen.getByDisplayValue('10000')).toBeInTheDocument()
  })

  it('calls delete mutation when the delete button is clicked', async () => {
    const deleteMutate = vi.fn()
    useBudgetsListMock.mockReturnValue({
      data: [{ id: 1, category_id: 1, year_month: '2026-07', is_business: false, budget_amount: '5000' }],
      isLoading: false,
      isError: false,
    })
    useCreateBudgetMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useDeleteBudgetMock.mockReturnValue({ mutate: deleteMutate, isPending: false })

    const user = userEvent.setup()
    render(<BudgetsPage />)

    await user.click(screen.getByRole('button', { name: '予算を削除' }))

    expect(deleteMutate).toHaveBeenCalledWith(1, expect.anything())
  })
})
