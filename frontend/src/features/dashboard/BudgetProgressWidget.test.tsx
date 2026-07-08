import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BudgetProgressWidget } from './BudgetProgressWidget'

const useBudgetProgressMock = vi.fn()

vi.mock('./queries', () => ({
  useBudgetProgress: () => useBudgetProgressMock(),
}))

describe('BudgetProgressWidget', () => {
  it('shows an error message when the request fails', () => {
    useBudgetProgressMock.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    render(<BudgetProgressWidget />)
    expect(screen.getByText('データの取得に失敗しました')).toBeInTheDocument()
  })

  it('shows an empty state when no budgets are configured', () => {
    useBudgetProgressMock.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<BudgetProgressWidget />)
    expect(screen.getByText('予算が設定されていません')).toBeInTheDocument()
  })

  it('renders progress without an over-budget warning when under budget', () => {
    useBudgetProgressMock.mockReturnValue({
      data: [
        {
          category_id: 1,
          category_name: '交通費',
          budget_amount: '10000',
          spent_amount: '5000',
          progress_ratio: '0.5',
        },
      ],
      isLoading: false,
      isError: false,
    })
    render(<BudgetProgressWidget />)
    expect(screen.getByText('交通費')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
    expect(screen.queryByText(/予算超過/)).not.toBeInTheDocument()
  })

  it('shows an over-budget warning when spending exceeds the budget', () => {
    useBudgetProgressMock.mockReturnValue({
      data: [
        {
          category_id: 2,
          category_name: '交際費',
          budget_amount: '10000',
          spent_amount: '15000',
          progress_ratio: '1.5',
        },
      ],
      isLoading: false,
      isError: false,
    })
    render(<BudgetProgressWidget />)
    expect(screen.getByText(/予算超過/)).toBeInTheDocument()
  })
})
