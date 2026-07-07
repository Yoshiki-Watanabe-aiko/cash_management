import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Transaction, Transfer, TransferCreate } from '@/api/types'

export function useUnlinkedTransferCandidates() {
  return useQuery({
    queryKey: ['transfers', 'unlinked-candidates'],
    queryFn: () => apiClient.get<Transaction[]>('/api/transfers/unlinked-candidates'),
  })
}

export function useCreateTransferLink() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: TransferCreate) => apiClient.post<Transfer>('/api/transfers', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfers'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
