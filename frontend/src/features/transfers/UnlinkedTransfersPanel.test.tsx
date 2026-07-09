import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UnlinkedTransfersPanel } from './UnlinkedTransfersPanel'
import type { Transaction } from '@/api/types'

const useUnlinkedTransferCandidatesMock = vi.fn()
const useCreateTransferLinkMock = vi.fn()

vi.mock('./queries', () => ({
  useUnlinkedTransferCandidates: () => useUnlinkedTransferCandidatesMock(),
  useCreateTransferLink: () => useCreateTransferLinkMock(),
}))

vi.mock('@/features/reference/queries', () => ({
  useAccounts: () => ({
    data: [
      {
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
      },
      {
        id: 2,
        institution_id: 2,
        account_name: '三井住友銀行 個人',
        account_type: 'bank',
        is_business: false,
        is_active: true,
        default_business_ratio: '0',
        tracks_balance: true,
        balance_method: 'cumulative',
        opening_balance: '50000',
        opening_balance_date: '2026-01-01',
        moneyforward_account_name: null,
        card_last4: null,
      },
    ],
  }),
}))

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

describe('UnlinkedTransfersPanel', () => {
  beforeEach(() => {
    useCreateTransferLinkMock.mockReturnValue({ mutate: vi.fn(), isPending: false })
  })

  it('shows an error message when candidates fail to load', () => {
    useUnlinkedTransferCandidatesMock.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    render(<UnlinkedTransfersPanel />)
    expect(screen.getByText('候補取引の取得に失敗しました')).toBeInTheDocument()
  })

  it('shows an empty state when there are no unlinked candidates', () => {
    useUnlinkedTransferCandidatesMock.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<UnlinkedTransfersPanel />)
    expect(screen.getByText('未紐づけの候補取引はありません')).toBeInTheDocument()
  })

  it('renders separate outgoing/incoming selects once candidates load, with the link button disabled until both sides are chosen', () => {
    useUnlinkedTransferCandidatesMock.mockReturnValue({
      data: [
        makeTransaction({ id: 1, amount: '-3000', description: '振替出金' }),
        makeTransaction({ id: 2, amount: '3000', description: '振替入金' }),
      ],
      isLoading: false,
      isError: false,
    })
    render(<UnlinkedTransfersPanel />)

    expect(screen.getByLabelText('出金側')).toBeInTheDocument()
    expect(screen.getByLabelText('入金側')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /紐づける/ })).toBeDisabled()
  })
})
