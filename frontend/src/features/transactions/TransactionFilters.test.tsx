import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { TransactionFiltersBar } from './TransactionFilters'
import type { TransactionFilters as Filters } from './queries'

vi.mock('@/features/reference/queries', () => ({
  useAccounts: () => ({ data: [] }),
  useCategories: () => ({ data: [] }),
}))

const baseFilters: Filters = { page: 1, pageSize: 20 }

describe('TransactionFiltersBar', () => {
  it('updates dateFrom and resets the page to 1', () => {
    const onChange = vi.fn()
    render(
      <TransactionFiltersBar
        filters={{ ...baseFilters, page: 3 }}
        onChange={onChange}
        onRecategorize={vi.fn()}
        isRecategorizing={false}
      />,
    )

    fireEvent.change(screen.getByLabelText('期間（開始）'), { target: { value: '2026-07-01' } })

    expect(onChange).toHaveBeenCalledWith({ ...baseFilters, page: 1, dateFrom: '2026-07-01' })
  })

  it('toggles uncategorizedOnly and resets the page to 1', () => {
    const onChange = vi.fn()
    render(
      <TransactionFiltersBar
        filters={{ ...baseFilters, page: 2 }}
        onChange={onChange}
        onRecategorize={vi.fn()}
        isRecategorizing={false}
      />,
    )

    fireEvent.click(screen.getByLabelText('未分類のみ'))

    expect(onChange).toHaveBeenCalledWith({ ...baseFilters, page: 1, uncategorizedOnly: true })
  })

  it('calls onRecategorize when the button is clicked', () => {
    const onRecategorize = vi.fn()
    render(
      <TransactionFiltersBar
        filters={baseFilters}
        onChange={vi.fn()}
        onRecategorize={onRecategorize}
        isRecategorizing={false}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /未分類の取引にルールを再適用/ }))

    expect(onRecategorize).toHaveBeenCalledTimes(1)
  })

  it('disables the recategorize button while a recategorize request is in flight', () => {
    render(
      <TransactionFiltersBar
        filters={baseFilters}
        onChange={vi.fn()}
        onRecategorize={vi.fn()}
        isRecategorizing
      />,
    )

    expect(screen.getByRole('button', { name: /未分類の取引にルールを再適用/ })).toBeDisabled()
  })
})
