import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ApiError } from '@/api/client'
import { UnlinkedTransfersPanel } from '@/features/transfers/UnlinkedTransfersPanel'
import { TransactionFiltersBar } from './TransactionFilters'
import { TransactionsTable } from './TransactionsTable'
import { useRecategorizeTransactions, useTransactionsList, type TransactionFilters } from './queries'

const DEFAULT_FILTERS: TransactionFilters = { page: 1, pageSize: 50 }

export function TransactionsPage() {
  const [filters, setFilters] = useState<TransactionFilters>(DEFAULT_FILTERS)
  const { data, isLoading, isError } = useTransactionsList(filters)
  const recategorize = useRecategorizeTransactions()
  const [recategorizeError, setRecategorizeError] = useState<string>()

  const handleRecategorize = () => {
    setRecategorizeError(undefined)
    recategorize.mutate(undefined, {
      onError: (error) => {
        setRecategorizeError(error instanceof ApiError ? error.message : '再分類に失敗しました')
      },
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">取引管理</h1>
        <p className="text-sm text-muted-foreground">分類の補正・事業按分比率の調整・振替の手動紐づけを行います</p>
      </div>

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">取引一覧</TabsTrigger>
          <TabsTrigger value="transfers">振替の手動紐づけ</TabsTrigger>
        </TabsList>
        <TabsContent value="list" className="space-y-4">
          <TransactionFiltersBar
            filters={filters}
            onChange={setFilters}
            onRecategorize={handleRecategorize}
            isRecategorizing={recategorize.isPending}
          />
          {recategorizeError && <p className="text-sm text-destructive">{recategorizeError}</p>}
          <TransactionsTable
            transactions={data?.items ?? []}
            total={data?.total ?? 0}
            isLoading={isLoading}
            isError={isError}
            filters={filters}
            onFiltersChange={setFilters}
          />
        </TabsContent>
        <TabsContent value="transfers">
          <UnlinkedTransfersPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}
