import { useId, useState } from 'react'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
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
import { ApiError } from '@/api/client'
import { useAccounts, useCategories } from '@/features/reference/queries'
import { useCreateTransaction } from './queries'

const NO_ACCOUNT_VALUE = 'none'
const UNCATEGORIZED_VALUE = 'uncategorized'

type TransactionKind = 'expense' | 'income'

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10)
}

export function CreateTransactionDialog() {
  const { data: accounts } = useAccounts()
  const { data: categories } = useCategories()
  const createTransaction = useCreateTransaction()
  const accountSelectId = useId()
  const categorySelectId = useId()
  const kindSelectId = useId()

  const [open, setOpen] = useState(false)
  const [transactionDate, setTransactionDate] = useState(todayIsoDate())
  const [accountId, setAccountId] = useState(NO_ACCOUNT_VALUE)
  const [kind, setKind] = useState<TransactionKind>('expense')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [categoryId, setCategoryId] = useState(UNCATEGORIZED_VALUE)
  const [businessRatio, setBusinessRatio] = useState('100')
  const [errorMessage, setErrorMessage] = useState<string>()

  const reset = () => {
    setTransactionDate(todayIsoDate())
    setAccountId(NO_ACCOUNT_VALUE)
    setKind('expense')
    setAmount('')
    setDescription('')
    setCategoryId(UNCATEGORIZED_VALUE)
    setBusinessRatio('100')
    setErrorMessage(undefined)
  }

  const handleSubmit = () => {
    if (!description.trim()) {
      setErrorMessage('摘要を入力してください')
      return
    }
    const parsedAmount = Number(amount)
    if (!amount.trim() || Number.isNaN(parsedAmount) || parsedAmount <= 0) {
      setErrorMessage('金額には0より大きい数値を入力してください')
      return
    }
    const parsedBusinessRatio = Number(businessRatio)
    if (
      businessRatio.trim() === '' ||
      Number.isNaN(parsedBusinessRatio) ||
      parsedBusinessRatio < 0 ||
      parsedBusinessRatio > 100
    ) {
      setErrorMessage('事業按分率は0〜100の数値を入力してください')
      return
    }

    setErrorMessage(undefined)
    createTransaction.mutate(
      {
        account_id: accountId === NO_ACCOUNT_VALUE ? null : Number(accountId),
        transaction_date: transactionDate,
        amount: kind === 'expense' ? -Math.abs(parsedAmount) : Math.abs(parsedAmount),
        description: description.trim(),
        category_id: categoryId === UNCATEGORIZED_VALUE ? null : Number(categoryId),
        business_ratio: parsedBusinessRatio,
      },
      {
        onSuccess: () => {
          reset()
          setOpen(false)
        },
        onError: (error) => {
          setErrorMessage(error instanceof ApiError ? error.message : '登録に失敗しました')
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
          取引を追加
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
            <DialogTitle>取引を手動登録</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="txn-date">取引日</Label>
              <Input
                id="txn-date"
                type="date"
                value={transactionDate}
                onChange={(event) => setTransactionDate(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={accountSelectId}>口座</Label>
              <Select value={accountId} onValueChange={setAccountId}>
                <SelectTrigger id={accountSelectId} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_ACCOUNT_VALUE}>現金など(口座に紐付けない)</SelectItem>
                  {accounts?.map((account) => (
                    <SelectItem key={account.id} value={String(account.id)}>
                      {account.account_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor={kindSelectId}>種別</Label>
                <Select value={kind} onValueChange={(value) => setKind(value as TransactionKind)}>
                  <SelectTrigger id={kindSelectId} className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="expense">支出</SelectItem>
                    <SelectItem value="income">収入</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="txn-amount">金額</Label>
                <Input
                  id="txn-amount"
                  type="number"
                  min={0}
                  step="1"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="txn-description">摘要</Label>
              <Input
                id="txn-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={categorySelectId}>カテゴリ</Label>
              <Select value={categoryId} onValueChange={setCategoryId}>
                <SelectTrigger id={categorySelectId} className="w-full">
                  <SelectValue />
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
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="txn-business-ratio">事業按分率(%)</Label>
              <Input
                id="txn-business-ratio"
                type="number"
                min={0}
                max={100}
                step={1}
                value={businessRatio}
                onChange={(event) => setBusinessRatio(event.target.value)}
              />
            </div>
            {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createTransaction.isPending}>
              登録
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
