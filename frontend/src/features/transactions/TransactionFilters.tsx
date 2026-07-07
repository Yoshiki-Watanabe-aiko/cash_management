import { RotateCw, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAccounts, useCategories } from '@/features/reference/queries'
import type { TransactionFilters as Filters } from './queries'

const ALL_VALUE = 'all'

interface TransactionFiltersProps {
  filters: Filters
  onChange: (filters: Filters) => void
  onRecategorize: () => void
  isRecategorizing: boolean
}

export function TransactionFiltersBar({ filters, onChange, onRecategorize, isRecategorizing }: TransactionFiltersProps) {
  const { data: accounts } = useAccounts()
  const { data: categories } = useCategories()

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-card p-4">
      <div className="space-y-1.5">
        <Label htmlFor="filter-account">口座</Label>
        <Select
          value={filters.accountId ? String(filters.accountId) : ALL_VALUE}
          onValueChange={(value) =>
            onChange({ ...filters, accountId: value === ALL_VALUE ? undefined : Number(value), page: 1 })
          }
        >
          <SelectTrigger id="filter-account" className="w-44">
            <SelectValue placeholder="すべての口座" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_VALUE}>すべての口座</SelectItem>
            {accounts?.map((account) => (
              <SelectItem key={account.id} value={String(account.id)}>
                {account.account_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="filter-category">カテゴリ</Label>
        <Select
          value={filters.categoryId ? String(filters.categoryId) : ALL_VALUE}
          onValueChange={(value) =>
            onChange({ ...filters, categoryId: value === ALL_VALUE ? undefined : Number(value), page: 1 })
          }
        >
          <SelectTrigger id="filter-category" className="w-44">
            <SelectValue placeholder="すべてのカテゴリ" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_VALUE}>すべてのカテゴリ</SelectItem>
            {categories?.map((category) => (
              <SelectItem key={category.id} value={String(category.id)}>
                {category.category_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="filter-date-from">期間（開始）</Label>
        <Input
          id="filter-date-from"
          type="date"
          className="w-40"
          value={filters.dateFrom ?? ''}
          onChange={(event) => onChange({ ...filters, dateFrom: event.target.value || undefined, page: 1 })}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="filter-date-to">期間（終了）</Label>
        <Input
          id="filter-date-to"
          type="date"
          className="w-40"
          value={filters.dateTo ?? ''}
          onChange={(event) => onChange({ ...filters, dateTo: event.target.value || undefined, page: 1 })}
        />
      </div>

      <label className="flex items-center gap-2 pb-2 text-sm text-foreground">
        <input
          type="checkbox"
          className="size-4 rounded border-input accent-primary"
          checked={filters.uncategorizedOnly ?? false}
          onChange={(event) => onChange({ ...filters, uncategorizedOnly: event.target.checked, page: 1 })}
        />
        未分類のみ
      </label>

      <Button
        type="button"
        variant="secondary"
        onClick={onRecategorize}
        disabled={isRecategorizing}
        className="ml-auto"
      >
        {isRecategorizing ? <RotateCw className="animate-spin" /> : <Sparkles />}
        未分類の取引にルールを再適用
      </Button>
    </div>
  )
}
