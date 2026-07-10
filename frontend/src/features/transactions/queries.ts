import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, buildQueryString } from '@/api/client'
import type {
  RecategorizeResult,
  Transaction,
  TransactionCreate,
  TransactionListResponse,
  TransactionUpdate,
} from '@/api/types'

export interface TransactionFilters {
  accountId?: number
  categoryId?: number
  dateFrom?: string
  dateTo?: string
  uncategorizedOnly?: boolean
  page: number
  pageSize: number
}

export function useTransactionsList(filters: TransactionFilters) {
  return useQuery({
    queryKey: ['transactions', filters],
    queryFn: () =>
      apiClient.get<TransactionListResponse>(
        `/api/transactions${buildQueryString({
          account_id: filters.accountId,
          category_id: filters.categoryId,
          date_from: filters.dateFrom,
          date_to: filters.dateTo,
          uncategorized_only: filters.uncategorizedOnly,
          page: filters.page,
          page_size: filters.pageSize,
        })}`,
      ),
  })
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, update }: { id: number; update: TransactionUpdate }) =>
      apiClient.patch<Transaction>(`/api/transactions/${id}`, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['transfers'] })
    },
  })
}

export function useCreateTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: TransactionCreate) => apiClient.post<Transaction>('/api/transactions', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useRecategorizeTransactions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => apiClient.post<RecategorizeResult>('/api/transactions/recategorize'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
