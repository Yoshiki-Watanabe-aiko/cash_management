import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CategoryRulesPage } from './CategoryRulesPage'

const useCategoryRulesListMock = vi.fn()
const useCreateCategoryRuleMock = vi.fn()
const useUpdateCategoryRuleMock = vi.fn()
const useDeleteCategoryRuleMock = vi.fn()

vi.mock('./queries', () => ({
  useCategoryRulesList: () => useCategoryRulesListMock(),
  useCreateCategoryRule: () => useCreateCategoryRuleMock(),
  useUpdateCategoryRule: () => useUpdateCategoryRuleMock(),
  useDeleteCategoryRule: () => useDeleteCategoryRuleMock(),
}))

vi.mock('@/features/reference/queries', () => ({
  useCategories: () => ({ data: [{ id: 1, category_name: '食費' }] }),
}))

describe('CategoryRulesPage', () => {
  it('shows an error message when rules fail to load', () => {
    useCategoryRulesListMock.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    useCreateCategoryRuleMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useDeleteCategoryRuleMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<CategoryRulesPage />)

    expect(screen.getByText('ルールの取得に失敗しました')).toBeInTheDocument()
  })

  it('shows an empty state when there are no rules', () => {
    useCategoryRulesListMock.mockReturnValue({ data: [], isLoading: false, isError: false })
    useCreateCategoryRuleMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useDeleteCategoryRuleMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<CategoryRulesPage />)

    expect(screen.getByText('ルールがまだ登録されていません')).toBeInTheDocument()
  })

  it('renders a rule row with keyword and category name', () => {
    useCategoryRulesListMock.mockReturnValue({
      data: [{ id: 1, keyword_pattern: 'スーパー', category_id: 1, priority: 10 }],
      isLoading: false,
      isError: false,
    })
    useCreateCategoryRuleMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useDeleteCategoryRuleMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<CategoryRulesPage />)

    expect(screen.getByText('スーパー')).toBeInTheDocument()
    expect(screen.getByText('食費')).toBeInTheDocument()
    expect(screen.getByDisplayValue('10')).toBeInTheDocument()
  })

  it('calls delete mutation when the delete button is clicked', async () => {
    const deleteMutate = vi.fn()
    useCategoryRulesListMock.mockReturnValue({
      data: [{ id: 1, keyword_pattern: 'スーパー', category_id: 1, priority: 10 }],
      isLoading: false,
      isError: false,
    })
    useCreateCategoryRuleMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useDeleteCategoryRuleMock.mockReturnValue({ mutate: deleteMutate, isPending: false })

    const user = userEvent.setup()
    render(<CategoryRulesPage />)

    await user.click(screen.getByRole('button', { name: 'ルールを削除' }))

    expect(deleteMutate).toHaveBeenCalledWith(1, expect.anything())
  })
})
