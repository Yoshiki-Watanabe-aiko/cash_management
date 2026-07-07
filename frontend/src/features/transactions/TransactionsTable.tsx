import { useEffect, useMemo, useState } from 'react'
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from '@tanstack/react-table'
import { ArrowLeft, ArrowRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAccounts, useCategories } from '@/features/reference/queries'
import { formatCurrency, formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import { ApiError } from '@/api/client'
import type { Transaction } from '@/api/types'
import { useUpdateTransaction, type TransactionFilters } from './queries'

const UNCATEGORIZED_VALUE = 'uncategorized'

interface TransactionsTableProps {
  transactions: Transaction[]
  total: number
  isLoading: boolean
  isError: boolean
  filters: TransactionFilters
  onFiltersChange: (filters: TransactionFilters) => void
}

function BusinessRatioCell({ transaction }: { transaction: Transaction }) {
  const [value, setValue] = useState(String(transaction.business_ratio))
  const [errorMessage, setErrorMessage] = useState<string>()
  const updateTransaction = useUpdateTransaction()

  useEffect(() => {
    setValue(String(transaction.business_ratio))
  }, [transaction.business_ratio])

  const commit = () => {
    const parsed = Number(value)
    if (Number.isNaN(parsed) || parsed < 0 || parsed > 100) {
      setErrorMessage('0〜100の数値を入力してください')
      setValue(String(transaction.business_ratio))
      return
    }
    if (parsed === Number(transaction.business_ratio)) return
    setErrorMessage(undefined)
    updateTransaction.mutate(
      { id: transaction.id, update: { business_ratio: parsed } },
      {
        onError: (error) => {
          setErrorMessage(error instanceof ApiError ? error.message : '更新に失敗しました')
          setValue(String(transaction.business_ratio))
        },
      },
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1">
        <Input
          type="number"
          min={0}
          max={100}
          step={1}
          value={value}
          aria-label="事業按分率"
          aria-invalid={Boolean(errorMessage)}
          onChange={(event) => setValue(event.target.value)}
          onBlur={commit}
          className="h-8 w-20"
        />
        <span className="text-xs text-muted-foreground">%</span>
      </div>
      {errorMessage && <span className="text-xs text-destructive">{errorMessage}</span>}
    </div>
  )
}

function CategoryCell({ transaction }: { transaction: Transaction }) {
  const { data: categories } = useCategories()
  const updateTransaction = useUpdateTransaction()
  const [errorMessage, setErrorMessage] = useState<string>()

  return (
    <div className="flex flex-col gap-1">
      <Select
        value={transaction.category_id != null ? String(transaction.category_id) : UNCATEGORIZED_VALUE}
        onValueChange={(value) => {
          setErrorMessage(undefined)
          const category_id = value === UNCATEGORIZED_VALUE ? null : Number(value)
          updateTransaction.mutate(
            { id: transaction.id, update: { category_id } },
            {
              onError: (error) => {
                setErrorMessage(error instanceof ApiError ? error.message : '更新に失敗しました')
              },
            },
          )
        }}
      >
        <SelectTrigger size="sm" className="w-40" aria-label="カテゴリ">
          <SelectValue placeholder="未分類" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={UNCATEGORIZED_VALUE}>未分類</SelectItem>
          {categories?.map((category) => (
            <SelectItem key={category.id} value={String(category.id)}>
              {category.category_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {errorMessage && <span className="text-xs text-destructive">{errorMessage}</span>}
    </div>
  )
}

export function TransactionsTable({
  transactions,
  total,
  isLoading,
  isError,
  filters,
  onFiltersChange,
}: TransactionsTableProps) {
  const { data: accounts } = useAccounts()
  const accountNameById = useMemo(
    () => new Map(accounts?.map((account) => [account.id, account.account_name])),
    [accounts],
  )

  const columns = useMemo<ColumnDef<Transaction>[]>(
    () => [
      {
        accessorKey: 'transaction_date',
        header: '取引日',
        cell: ({ row }) => formatDate(row.original.transaction_date),
      },
      {
        accessorKey: 'account_id',
        header: '口座',
        cell: ({ row }) => accountNameById.get(row.original.account_id ?? -1) ?? '—',
      },
      {
        accessorKey: 'description',
        header: '摘要',
        cell: ({ row }) => <span className="block max-w-xs truncate">{row.original.description}</span>,
      },
      {
        accessorKey: 'category_id',
        header: 'カテゴリ',
        cell: ({ row }) => <CategoryCell key={row.original.id} transaction={row.original} />,
      },
      {
        accessorKey: 'business_ratio',
        header: '事業按分',
        cell: ({ row }) => <BusinessRatioCell key={row.original.id} transaction={row.original} />,
      },
      {
        accessorKey: 'amount',
        header: '金額',
        cell: ({ row }) => (
          <span
            className={cn(
              'font-medium tabular-nums',
              Number(row.original.amount) < 0 ? 'text-expense' : 'text-income',
            )}
          >
            {formatCurrency(row.original.amount)}
          </span>
        ),
      },
      {
        accessorKey: 'is_transferred',
        header: '振替',
        cell: ({ row }) => (row.original.is_transferred ? <Badge variant="secondary">振替</Badge> : null),
      },
    ],
    [accountNameById],
  )

  const table = useReactTable({
    data: transactions,
    columns,
    getRowId: (row) => String(row.id),
    getCoreRowModel: getCoreRowModel(),
  })

  const pageCount = Math.max(1, Math.ceil(total / filters.pageSize))

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={`skeleton-${index}`}>
                  <TableCell colSpan={columns.length}>
                    <Skeleton className="h-6 w-full" />
                  </TableCell>
                </TableRow>
              ))}
            {!isLoading && isError && (
              <TableRow>
                <TableCell colSpan={columns.length} className="py-8 text-center text-destructive">
                  取引の取得に失敗しました
                </TableCell>
              </TableRow>
            )}
            {!isLoading && !isError && transactions.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length} className="py-8 text-center text-muted-foreground">
                  該当する取引がありません
                </TableCell>
              </TableRow>
            )}
            {!isLoading &&
              !isError &&
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                  ))}
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          全 {total} 件中 {transactions.length === 0 ? 0 : (filters.page - 1) * filters.pageSize + 1}〜
          {(filters.page - 1) * filters.pageSize + transactions.length} 件を表示
        </span>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={filters.page <= 1}
            onClick={() => onFiltersChange({ ...filters, page: filters.page - 1 })}
          >
            <ArrowLeft />
            前へ
          </Button>
          <span>
            {filters.page} / {pageCount}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={filters.page >= pageCount}
            onClick={() => onFiltersChange({ ...filters, page: filters.page + 1 })}
          >
            次へ
            <ArrowRight />
          </Button>
        </div>
      </div>
    </div>
  )
}
