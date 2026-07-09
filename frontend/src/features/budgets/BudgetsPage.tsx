import { useEffect, useId, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ApiError } from '@/api/client'
import type { Budget } from '@/api/types'
import { useCategories } from '@/features/reference/queries'
import { useBudgetsList, useCreateBudget, useDeleteBudget, useUpdateBudget } from './queries'

const ALL_VALUE = 'all'
const BUSINESS_VALUE = 'business'
const PERSONAL_VALUE = 'personal'

function currentYearMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function BudgetAmountCell({ budget }: { budget: Budget }) {
  const [value, setValue] = useState(budget.budget_amount)
  const [errorMessage, setErrorMessage] = useState<string>()
  const updateBudget = useUpdateBudget()

  useEffect(() => {
    setValue(budget.budget_amount)
  }, [budget.budget_amount])

  const commit = () => {
    const parsed = Number(value)
    if (Number.isNaN(parsed) || parsed <= 0) {
      setErrorMessage('0より大きい数値を入力してください')
      setValue(budget.budget_amount)
      return
    }
    if (parsed === Number(budget.budget_amount)) return
    setErrorMessage(undefined)
    updateBudget.mutate(
      { id: budget.id, update: { budget_amount: parsed } },
      {
        onError: (error) => {
          setErrorMessage(error instanceof ApiError ? error.message : '更新に失敗しました')
          setValue(budget.budget_amount)
        },
      },
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <Input
        type="number"
        min={0}
        step={1}
        value={value}
        aria-label="予算金額"
        aria-invalid={Boolean(errorMessage)}
        onChange={(event) => setValue(event.target.value)}
        onBlur={commit}
        className="h-8 w-32"
      />
      {errorMessage && <span className="text-xs text-destructive">{errorMessage}</span>}
    </div>
  )
}

function CreateBudgetDialog({ yearMonth }: { yearMonth: string }) {
  const { data: categories } = useCategories()
  const createBudget = useCreateBudget()
  const categorySelectId = useId()
  const isBusinessSelectId = useId()

  const [open, setOpen] = useState(false)
  const [categoryId, setCategoryId] = useState('')
  const [isBusiness, setIsBusiness] = useState(BUSINESS_VALUE)
  const [amount, setAmount] = useState('')
  const [errorMessage, setErrorMessage] = useState<string>()

  const reset = () => {
    setCategoryId('')
    setIsBusiness(BUSINESS_VALUE)
    setAmount('')
    setErrorMessage(undefined)
  }

  const handleSubmit = () => {
    const parsedAmount = Number(amount)
    if (!categoryId) {
      setErrorMessage('カテゴリを選択してください')
      return
    }
    if (Number.isNaN(parsedAmount) || parsedAmount <= 0) {
      setErrorMessage('0より大きい金額を入力してください')
      return
    }
    setErrorMessage(undefined)
    createBudget.mutate(
      {
        category_id: Number(categoryId),
        year_month: yearMonth,
        is_business: isBusiness === BUSINESS_VALUE,
        budget_amount: parsedAmount,
      },
      {
        onSuccess: () => {
          reset()
          setOpen(false)
        },
        onError: (error) => {
          setErrorMessage(error instanceof ApiError ? error.message : '作成に失敗しました')
        },
      },
    )
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) reset()
      }}
    >
      <DialogTrigger asChild>
        <Button type="button">
          <Plus />
          予算を追加
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            handleSubmit()
          }}
        >
          <DialogHeader>
            <DialogTitle>{yearMonth}の予算を追加</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor={categorySelectId}>カテゴリ</Label>
              <Select value={categoryId} onValueChange={setCategoryId}>
                <SelectTrigger id={categorySelectId} className="w-full">
                  <SelectValue placeholder="カテゴリを選択" />
                </SelectTrigger>
                <SelectContent>
                  {categories?.map((category) => (
                    <SelectItem key={category.id} value={String(category.id)}>
                      {category.category_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={isBusinessSelectId}>区分</Label>
              <Select value={isBusiness} onValueChange={setIsBusiness}>
                <SelectTrigger id={isBusinessSelectId} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={BUSINESS_VALUE}>事業</SelectItem>
                  <SelectItem value={PERSONAL_VALUE}>個人</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="budget-amount">予算金額</Label>
              <Input
                id="budget-amount"
                type="number"
                min={0}
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
              />
            </div>
            {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createBudget.isPending}>
              追加
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function BudgetsPage() {
  const [yearMonth, setYearMonth] = useState(currentYearMonth())
  const [isBusinessFilter, setIsBusinessFilter] = useState(ALL_VALUE)
  const { data: categories } = useCategories()
  const { data: budgets, isLoading, isError } = useBudgetsList({
    yearMonth,
    isBusiness: isBusinessFilter === ALL_VALUE ? undefined : isBusinessFilter === BUSINESS_VALUE,
  })
  const deleteBudget = useDeleteBudget()
  const [deleteError, setDeleteError] = useState<string>()

  const categoryNameById = new Map(categories?.map((category) => [category.id, category.category_name]))

  const handleDelete = (id: number) => {
    setDeleteError(undefined)
    deleteBudget.mutate(id, {
      onError: (error) => {
        setDeleteError(error instanceof ApiError ? error.message : '削除に失敗しました')
      },
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">予算管理</h1>
        <p className="text-sm text-muted-foreground">年月・個人/事業区分ごとの予算額を設定します</p>
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-card p-4">
        <div className="space-y-1.5">
          <Label htmlFor="budget-year-month">対象年月</Label>
          <Input
            id="budget-year-month"
            type="month"
            className="w-40"
            value={yearMonth}
            onChange={(event) => setYearMonth(event.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="budget-business-filter">区分</Label>
          <Select value={isBusinessFilter} onValueChange={setIsBusinessFilter}>
            <SelectTrigger id="budget-business-filter" className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_VALUE}>すべて</SelectItem>
              <SelectItem value={BUSINESS_VALUE}>事業</SelectItem>
              <SelectItem value={PERSONAL_VALUE}>個人</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <CreateBudgetDialog yearMonth={yearMonth} />
      </div>

      {deleteError && <p className="text-sm text-destructive">{deleteError}</p>}

      <Card>
        <CardHeader>
          <CardTitle>{yearMonth}の予算一覧</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>カテゴリ</TableHead>
                  <TableHead>区分</TableHead>
                  <TableHead>予算金額</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading &&
                  Array.from({ length: 3 }).map((_, index) => (
                    <TableRow key={`skeleton-${index}`}>
                      <TableCell colSpan={4}>
                        <Skeleton className="h-6 w-full" />
                      </TableCell>
                    </TableRow>
                  ))}
                {!isLoading && isError && (
                  <TableRow>
                    <TableCell colSpan={4} className="py-8 text-center text-destructive">
                      予算の取得に失敗しました
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading && !isError && budgets && budgets.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                      この年月の予算はまだ設定されていません
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading &&
                  !isError &&
                  budgets?.map((budget) => (
                    <TableRow key={budget.id}>
                      <TableCell>{categoryNameById.get(budget.category_id) ?? '—'}</TableCell>
                      <TableCell>{budget.is_business ? '事業' : '個人'}</TableCell>
                      <TableCell>
                        <BudgetAmountCell budget={budget} />
                      </TableCell>
                      <TableCell>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          aria-label="予算を削除"
                          onClick={() => handleDelete(budget.id)}
                        >
                          <Trash2 />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
