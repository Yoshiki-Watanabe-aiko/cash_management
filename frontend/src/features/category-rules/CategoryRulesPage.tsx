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
import type { CategoryRule } from '@/api/types'
import { useCategories } from '@/features/reference/queries'
import {
  useCategoryRulesList,
  useCreateCategoryRule,
  useDeleteCategoryRule,
  useUpdateCategoryRule,
} from './queries'

function PriorityCell({ rule }: { rule: CategoryRule }) {
  const [value, setValue] = useState(String(rule.priority))
  const [errorMessage, setErrorMessage] = useState<string>()
  const updateRule = useUpdateCategoryRule()

  useEffect(() => {
    setValue(String(rule.priority))
  }, [rule.priority])

  const commit = () => {
    if (value.trim() === '') {
      setErrorMessage('整数を入力してください')
      setValue(String(rule.priority))
      return
    }
    const parsed = Number(value)
    if (!Number.isInteger(parsed)) {
      setErrorMessage('整数を入力してください')
      setValue(String(rule.priority))
      return
    }
    if (parsed === rule.priority) return
    setErrorMessage(undefined)
    updateRule.mutate(
      { id: rule.id, update: { priority: parsed } },
      {
        onError: (error) => {
          setErrorMessage(error instanceof ApiError ? error.message : '更新に失敗しました')
          setValue(String(rule.priority))
        },
      },
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <Input
        type="number"
        step={1}
        value={value}
        aria-label="優先度"
        aria-invalid={Boolean(errorMessage)}
        onChange={(event) => setValue(event.target.value)}
        onBlur={commit}
        className="h-8 w-20"
      />
      {errorMessage && <span className="text-xs text-destructive">{errorMessage}</span>}
    </div>
  )
}

function CreateCategoryRuleDialog() {
  const { data: categories } = useCategories()
  const createRule = useCreateCategoryRule()
  const categorySelectId = useId()

  const [open, setOpen] = useState(false)
  const [keywordPattern, setKeywordPattern] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [priority, setPriority] = useState('100')
  const [errorMessage, setErrorMessage] = useState<string>()

  const reset = () => {
    setKeywordPattern('')
    setCategoryId('')
    setPriority('100')
    setErrorMessage(undefined)
  }

  const handleSubmit = () => {
    if (!keywordPattern.trim()) {
      setErrorMessage('キーワードを入力してください')
      return
    }
    if (!categoryId) {
      setErrorMessage('カテゴリを選択してください')
      return
    }
    if (priority.trim() === '' || !Number.isInteger(Number(priority))) {
      setErrorMessage('優先度は整数で入力してください')
      return
    }
    const parsedPriority = Number(priority)
    setErrorMessage(undefined)
    createRule.mutate(
      { keyword_pattern: keywordPattern.trim(), category_id: Number(categoryId), priority: parsedPriority },
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
          ルールを追加
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
            <DialogTitle>カテゴリ自動分類ルールを追加</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="rule-keyword">キーワード（部分一致）</Label>
              <Input
                id="rule-keyword"
                value={keywordPattern}
                onChange={(event) => setKeywordPattern(event.target.value)}
              />
            </div>
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
              <Label htmlFor="rule-priority">優先度（値が小さいほど優先）</Label>
              <Input
                id="rule-priority"
                type="number"
                step={1}
                value={priority}
                onChange={(event) => setPriority(event.target.value)}
              />
            </div>
            {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createRule.isPending}>
              追加
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function CategoryRulesPage() {
  const { data: rules, isLoading, isError } = useCategoryRulesList()
  const { data: categories } = useCategories()
  const deleteRule = useDeleteCategoryRule()
  const [deleteError, setDeleteError] = useState<string>()

  const categoryNameById = new Map(categories?.map((category) => [category.id, category.category_name]))

  const handleDelete = (id: number) => {
    setDeleteError(undefined)
    deleteRule.mutate(id, {
      onError: (error) => {
        setDeleteError(error instanceof ApiError ? error.message : '削除に失敗しました')
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">カテゴリ自動分類ルール</h1>
          <p className="text-sm text-muted-foreground">
            摘要とのキーワード部分一致で自動分類するルールを管理します（優先度が小さい順に評価）
          </p>
        </div>
        <CreateCategoryRuleDialog />
      </div>

      {deleteError && <p className="text-sm text-destructive">{deleteError}</p>}

      <Card>
        <CardHeader>
          <CardTitle>ルール一覧</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>優先度</TableHead>
                  <TableHead>キーワード</TableHead>
                  <TableHead>カテゴリ</TableHead>
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
                      ルールの取得に失敗しました
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading && !isError && rules && rules.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                      ルールがまだ登録されていません
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading &&
                  !isError &&
                  rules?.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell>
                        <PriorityCell rule={rule} />
                      </TableCell>
                      <TableCell>{rule.keyword_pattern}</TableCell>
                      <TableCell>{categoryNameById.get(rule.category_id) ?? '—'}</TableCell>
                      <TableCell>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          aria-label="ルールを削除"
                          onClick={() => handleDelete(rule.id)}
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
