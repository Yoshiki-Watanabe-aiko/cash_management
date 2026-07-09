import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { CategoryRule, CategoryRuleCreate, CategoryRuleUpdate } from '@/api/types'

export function useCategoryRulesList() {
  return useQuery({
    queryKey: ['category-rules'],
    queryFn: () => apiClient.get<CategoryRule[]>('/api/category-rules'),
  })
}

export function useCreateCategoryRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CategoryRuleCreate) => apiClient.post<CategoryRule>('/api/category-rules', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['category-rules'] })
    },
  })
}

export function useUpdateCategoryRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, update }: { id: number; update: CategoryRuleUpdate }) =>
      apiClient.patch<CategoryRule>(`/api/category-rules/${id}`, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['category-rules'] })
    },
  })
}

export function useDeleteCategoryRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiClient.delete<void>(`/api/category-rules/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['category-rules'] })
    },
  })
}
