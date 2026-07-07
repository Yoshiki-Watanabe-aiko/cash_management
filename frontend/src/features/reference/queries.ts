import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Account, Category } from '@/api/types'

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: () => apiClient.get<Account[]>('/api/accounts'),
    staleTime: 5 * 60_000,
  })
}

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => apiClient.get<Category[]>('/api/categories'),
    staleTime: 5 * 60_000,
  })
}
