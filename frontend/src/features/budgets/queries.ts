import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, buildQueryString } from '@/api/client'
import type { Budget, BudgetCreate, BudgetUpdate } from '@/api/types'

export interface BudgetFilters {
  yearMonth: string
  isBusiness?: boolean
}

export function useBudgetsList(filters: BudgetFilters) {
  return useQuery({
    queryKey: ['budgets', filters],
    queryFn: () =>
      apiClient.get<Budget[]>(
        `/api/budgets${buildQueryString({ year_month: filters.yearMonth, is_business: filters.isBusiness })}`,
      ),
  })
}

export function useCreateBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: BudgetCreate) => apiClient.post<Budget>('/api/budgets', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useUpdateBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, update }: { id: number; update: BudgetUpdate }) =>
      apiClient.patch<Budget>(`/api/budgets/${id}`, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useDeleteBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiClient.delete<void>(`/api/budgets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
