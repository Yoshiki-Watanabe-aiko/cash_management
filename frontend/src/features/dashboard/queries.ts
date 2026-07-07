import { useQuery } from '@tanstack/react-query'
import { apiClient, buildQueryString } from '@/api/client'
import type { BudgetProgressItem, CashflowSummary, CategoryAmount, NetWorthPoint } from '@/api/types'

export function useNetWorthHistory(months = 12) {
  return useQuery({
    queryKey: ['dashboard', 'net-worth-history', months],
    queryFn: () => apiClient.get<NetWorthPoint[]>(`/api/dashboard/net-worth-history${buildQueryString({ months })}`),
  })
}

export function useBudgetProgress(yearMonth?: string) {
  return useQuery({
    queryKey: ['dashboard', 'budget-progress', yearMonth],
    queryFn: () =>
      apiClient.get<BudgetProgressItem[]>(`/api/dashboard/budget-progress${buildQueryString({ year_month: yearMonth })}`),
  })
}

export function usePersonalCashflow(yearMonth?: string) {
  return useQuery({
    queryKey: ['dashboard', 'personal-cashflow', yearMonth],
    queryFn: () =>
      apiClient.get<CashflowSummary>(`/api/dashboard/personal-cashflow${buildQueryString({ year_month: yearMonth })}`),
  })
}

export function useCategoryBreakdown(yearMonth?: string) {
  return useQuery({
    queryKey: ['dashboard', 'category-breakdown', yearMonth],
    queryFn: () =>
      apiClient.get<CategoryAmount[]>(`/api/dashboard/category-breakdown${buildQueryString({ year_month: yearMonth })}`),
  })
}
