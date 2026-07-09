import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AccountsPage } from './AccountsPage'

const useCreateAccountMock = vi.fn()
const useUpdateAccountMock = vi.fn()

vi.mock('./queries', () => ({
  useCreateAccount: () => useCreateAccountMock(),
  useUpdateAccount: () => useUpdateAccountMock(),
}))

const useAccountsMock = vi.fn()
const useInstitutionsMock = vi.fn()

vi.mock('@/features/reference/queries', () => ({
  useAccounts: () => useAccountsMock(),
  useInstitutions: () => useInstitutionsMock(),
}))

function makeAccount(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    institution_id: 1,
    account_name: '楽天銀行 個人',
    account_type: 'bank',
    is_business: false,
    is_active: true,
    default_business_ratio: '0',
    tracks_balance: true,
    balance_method: 'cumulative',
    opening_balance: '100000',
    opening_balance_date: '2026-01-01',
    moneyforward_account_name: null,
    card_last4: null,
    ...overrides,
  }
}

describe('AccountsPage', () => {
  it('shows an error message when accounts fail to load', () => {
    useAccountsMock.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    useInstitutionsMock.mockReturnValue({ data: [] })
    useCreateAccountMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useUpdateAccountMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<AccountsPage />)

    expect(screen.getByText('口座の取得に失敗しました')).toBeInTheDocument()
  })

  it('shows an empty state when there are no accounts', () => {
    useAccountsMock.mockReturnValue({ data: [], isLoading: false, isError: false })
    useInstitutionsMock.mockReturnValue({ data: [] })
    useCreateAccountMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useUpdateAccountMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<AccountsPage />)

    expect(screen.getByText('口座がまだ登録されていません')).toBeInTheDocument()
  })

  it('renders an account row with institution name, type label, and status', () => {
    useAccountsMock.mockReturnValue({ data: [makeAccount()], isLoading: false, isError: false })
    useInstitutionsMock.mockReturnValue({ data: [{ id: 1, institution_name: '楽天銀行', institution_type: 'bank' }] })
    useCreateAccountMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
    useUpdateAccountMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<AccountsPage />)

    expect(screen.getByText('楽天銀行')).toBeInTheDocument()
    expect(screen.getByText('楽天銀行 個人')).toBeInTheDocument()
    expect(screen.getByText('銀行')).toBeInTheDocument()
    expect(screen.getByText('個人')).toBeInTheDocument()
    expect(screen.getByLabelText('有効/無効')).toBeInTheDocument()
  })
})
