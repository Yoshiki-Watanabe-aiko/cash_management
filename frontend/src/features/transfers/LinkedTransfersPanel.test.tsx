import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LinkedTransfersPanel } from './LinkedTransfersPanel'

const useLinkedTransfersMock = vi.fn()
const useDeleteTransferLinkMock = vi.fn()

vi.mock('./queries', () => ({
  useLinkedTransfers: () => useLinkedTransfersMock(),
  useDeleteTransferLink: () => useDeleteTransferLinkMock(),
}))

vi.mock('@/features/reference/queries', () => ({
  useAccounts: () => ({
    data: [{ id: 1, account_name: '楽天銀行 個人' }],
  }),
}))

describe('LinkedTransfersPanel', () => {
  it('shows an error message when the request fails', () => {
    useLinkedTransfersMock.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    useDeleteTransferLinkMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<LinkedTransfersPanel />)

    expect(screen.getByText('振替一覧の取得に失敗しました')).toBeInTheDocument()
  })

  it('shows an empty state when there are no linked transfers', () => {
    useLinkedTransfersMock.mockReturnValue({ data: [], isLoading: false, isError: false })
    useDeleteTransferLinkMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<LinkedTransfersPanel />)

    expect(screen.getByText('紐づけ済みの振替はありません')).toBeInTheDocument()
  })

  it('renders a linked transfer row with both transaction sides', () => {
    useLinkedTransfersMock.mockReturnValue({
      data: [
        {
          id: 1,
          match_confidence: 'manual',
          linked_at: '2026-07-01T00:00:00Z',
          from_transaction: { id: 10, transaction_date: '2026-07-01', amount: '-3000', description: '出金', account_id: 1 },
          to_transaction: { id: 11, transaction_date: '2026-07-01', amount: '3000', description: '入金', account_id: 1 },
        },
      ],
      isLoading: false,
      isError: false,
    })
    useDeleteTransferLinkMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

    render(<LinkedTransfersPanel />)

    expect(screen.getByText('手動')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '振替リンクを解除' })).toBeInTheDocument()
  })

  it('calls the delete mutation with the transfer id when unlink is clicked', async () => {
    const deleteMutate = vi.fn()
    useLinkedTransfersMock.mockReturnValue({
      data: [
        {
          id: 42,
          match_confidence: 'auto',
          linked_at: '2026-07-01T00:00:00Z',
          from_transaction: { id: 10, transaction_date: '2026-07-01', amount: '-3000', description: '出金', account_id: 1 },
          to_transaction: { id: 11, transaction_date: '2026-07-01', amount: '3000', description: '入金', account_id: 1 },
        },
      ],
      isLoading: false,
      isError: false,
    })
    useDeleteTransferLinkMock.mockReturnValue({ mutate: deleteMutate, isPending: false })

    const user = userEvent.setup()
    render(<LinkedTransfersPanel />)

    await user.click(screen.getByRole('button', { name: '振替リンクを解除' }))

    expect(deleteMutate).toHaveBeenCalledWith(42, expect.anything())
  })
})
