import { useId, useState } from 'react'
import { Plus } from 'lucide-react'
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
import type { Account, AccountCreate, AccountType, BalanceMethod } from '@/api/types'
import { useAccounts, useInstitutions } from '@/features/reference/queries'
import { useCreateAccount, useUpdateAccount } from './queries'

const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  bank: '銀行',
  credit_card: 'クレジットカード',
  securities: '証券',
  qr_payment: 'QR決済',
  loan: 'ローン',
}

const BALANCE_METHOD_LABELS: Record<BalanceMethod, string> = {
  cumulative: '初期残高+取引累積',
  moneyforward: 'マネーフォワードME連携',
  manual: '手動入力',
}

const BUSINESS_VALUE = 'business'
const PERSONAL_VALUE = 'personal'
const TRACKS_VALUE = 'tracks'
const NO_TRACKS_VALUE = 'no-tracks'

function IsActiveCell({ account }: { account: Account }) {
  const [errorMessage, setErrorMessage] = useState<string>()
  const updateAccount = useUpdateAccount()

  return (
    <div className="flex flex-col gap-1">
      <Select
        value={account.is_active ? 'active' : 'inactive'}
        onValueChange={(value) => {
          setErrorMessage(undefined)
          updateAccount.mutate(
            { id: account.id, update: { is_active: value === 'active' } },
            {
              onError: (error) => {
                setErrorMessage(error instanceof ApiError ? error.message : '更新に失敗しました')
              },
            },
          )
        }}
      >
        <SelectTrigger size="sm" className="w-28" aria-label="有効/無効">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="active">有効</SelectItem>
          <SelectItem value="inactive">無効</SelectItem>
        </SelectContent>
      </Select>
      {errorMessage && <span className="text-xs text-destructive">{errorMessage}</span>}
    </div>
  )
}

function CreateAccountDialog() {
  const { data: institutions } = useInstitutions()
  const createAccount = useCreateAccount()
  const institutionSelectId = useId()
  const accountTypeSelectId = useId()
  const isBusinessSelectId = useId()
  const tracksBalanceSelectId = useId()
  const balanceMethodSelectId = useId()

  const [open, setOpen] = useState(false)
  const [institutionId, setInstitutionId] = useState('')
  const [accountName, setAccountName] = useState('')
  const [accountType, setAccountType] = useState('')
  const [isBusiness, setIsBusiness] = useState(PERSONAL_VALUE)
  const [tracksBalance, setTracksBalance] = useState(NO_TRACKS_VALUE)
  const [balanceMethod, setBalanceMethod] = useState('')
  const [openingBalance, setOpeningBalance] = useState('')
  const [openingBalanceDate, setOpeningBalanceDate] = useState('')
  const [moneyforwardAccountName, setMoneyforwardAccountName] = useState('')
  const [cardLast4, setCardLast4] = useState('')
  const [errorMessage, setErrorMessage] = useState<string>()

  const reset = () => {
    setInstitutionId('')
    setAccountName('')
    setAccountType('')
    setIsBusiness(PERSONAL_VALUE)
    setTracksBalance(NO_TRACKS_VALUE)
    setBalanceMethod('')
    setOpeningBalance('')
    setOpeningBalanceDate('')
    setMoneyforwardAccountName('')
    setCardLast4('')
    setErrorMessage(undefined)
  }

  const handleSubmit = () => {
    if (!institutionId || !accountName.trim() || !accountType) {
      setErrorMessage('金融機関・口座名・口座種別は必須です')
      return
    }
    if (accountType === 'credit_card' && cardLast4 && cardLast4.length !== 4) {
      setErrorMessage('カード番号下4桁は4桁の数字で入力してください')
      return
    }
    if (tracksBalance === TRACKS_VALUE && !balanceMethod) {
      setErrorMessage('残高追跡を行う場合、残高算出方式は必須です')
      return
    }

    let parsedOpeningBalance: number | null = null
    if (tracksBalance === TRACKS_VALUE && balanceMethod === 'cumulative') {
      if (!openingBalance || !openingBalanceDate) {
        setErrorMessage('残高算出方式が「初期残高+取引累積」の場合、初期残高と初期残高基準日は必須です')
        return
      }
      parsedOpeningBalance = Number(openingBalance)
      if (Number.isNaN(parsedOpeningBalance)) {
        setErrorMessage('初期残高は数値で入力してください')
        return
      }
    }
    setErrorMessage(undefined)

    const payload: AccountCreate = {
      institution_id: Number(institutionId),
      account_name: accountName.trim(),
      account_type: accountType as AccountType,
      is_business: isBusiness === BUSINESS_VALUE,
      default_business_ratio: isBusiness === BUSINESS_VALUE ? 100 : 0,
      tracks_balance: tracksBalance === TRACKS_VALUE,
      balance_method: tracksBalance === TRACKS_VALUE ? (balanceMethod as BalanceMethod) || null : null,
      opening_balance: parsedOpeningBalance,
      opening_balance_date:
        tracksBalance === TRACKS_VALUE && balanceMethod === 'cumulative' && openingBalanceDate
          ? openingBalanceDate
          : null,
      moneyforward_account_name:
        tracksBalance === TRACKS_VALUE && balanceMethod === 'moneyforward' && moneyforwardAccountName.trim()
          ? moneyforwardAccountName.trim()
          : null,
      card_last4: accountType === 'credit_card' && cardLast4.length === 4 ? cardLast4 : null,
    }

    createAccount.mutate(payload, {
      onSuccess: () => {
        reset()
        setOpen(false)
      },
      onError: (error) => {
        setErrorMessage(error instanceof ApiError ? error.message : '作成に失敗しました')
      },
    })
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
          口座を追加
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
            <DialogTitle>口座を追加</DialogTitle>
          </DialogHeader>
          <div className="max-h-[70vh] space-y-3 overflow-y-auto">
            <div className="space-y-1.5">
              <Label htmlFor={institutionSelectId}>金融機関</Label>
              <Select value={institutionId} onValueChange={setInstitutionId}>
                <SelectTrigger id={institutionSelectId} className="w-full">
                  <SelectValue placeholder="金融機関を選択" />
                </SelectTrigger>
                <SelectContent>
                  {institutions?.map((institution) => (
                    <SelectItem key={institution.id} value={String(institution.id)}>
                      {institution.institution_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="account-name">口座表示名</Label>
              <Input
                id="account-name"
                value={accountName}
                onChange={(event) => setAccountName(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={accountTypeSelectId}>口座種別</Label>
              <Select value={accountType} onValueChange={setAccountType}>
                <SelectTrigger id={accountTypeSelectId} className="w-full">
                  <SelectValue placeholder="口座種別を選択" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(ACCOUNT_TYPE_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {accountType === 'credit_card' && (
              <div className="space-y-1.5">
                <Label htmlFor="card-last4">カード番号下4桁（任意）</Label>
                <Input
                  id="card-last4"
                  value={cardLast4}
                  maxLength={4}
                  onChange={(event) => setCardLast4(event.target.value.replace(/\D/g, ''))}
                />
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor={isBusinessSelectId}>個人/事業区分</Label>
              <Select value={isBusiness} onValueChange={setIsBusiness}>
                <SelectTrigger id={isBusinessSelectId} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={PERSONAL_VALUE}>個人</SelectItem>
                  <SelectItem value={BUSINESS_VALUE}>事業</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={tracksBalanceSelectId}>残高追跡</Label>
              <Select
                value={tracksBalance}
                onValueChange={(value) => {
                  setTracksBalance(value)
                  if (value === NO_TRACKS_VALUE) {
                    setBalanceMethod('')
                    setMoneyforwardAccountName('')
                  }
                }}
              >
                <SelectTrigger id={tracksBalanceSelectId} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_TRACKS_VALUE}>追跡しない（クレカ・都度払いQR決済）</SelectItem>
                  <SelectItem value={TRACKS_VALUE}>追跡する（銀行・証券・ローン・チャージ式QR決済）</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {tracksBalance === TRACKS_VALUE && (
              <div className="space-y-1.5">
                <Label htmlFor={balanceMethodSelectId}>残高算出方式</Label>
                <Select
                  value={balanceMethod}
                  onValueChange={(value) => {
                    setBalanceMethod(value)
                    if (value !== 'moneyforward') setMoneyforwardAccountName('')
                  }}
                >
                  <SelectTrigger id={balanceMethodSelectId} className="w-full">
                    <SelectValue placeholder="算出方式を選択" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(BALANCE_METHOD_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            {tracksBalance === TRACKS_VALUE && balanceMethod === 'cumulative' && (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="opening-balance">初期残高</Label>
                  <Input
                    id="opening-balance"
                    type="number"
                    value={openingBalance}
                    onChange={(event) => setOpeningBalance(event.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="opening-balance-date">初期残高基準日</Label>
                  <Input
                    id="opening-balance-date"
                    type="date"
                    value={openingBalanceDate}
                    onChange={(event) => setOpeningBalanceDate(event.target.value)}
                  />
                </div>
              </>
            )}
            {tracksBalance === TRACKS_VALUE && balanceMethod === 'moneyforward' && (
              <div className="space-y-1.5">
                <Label htmlFor="moneyforward-account-name">マネーフォワードME連携口座名</Label>
                <Input
                  id="moneyforward-account-name"
                  value={moneyforwardAccountName}
                  onChange={(event) => setMoneyforwardAccountName(event.target.value)}
                />
              </div>
            )}
            {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createAccount.isPending}>
              追加
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function AccountsPage() {
  const { data: accounts, isLoading, isError } = useAccounts()
  const { data: institutions } = useInstitutions()

  const institutionNameById = new Map(
    institutions?.map((institution) => [institution.id, institution.institution_name]),
  )

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">口座管理</h1>
          <p className="text-sm text-muted-foreground">
            銀行・クレジットカード・証券・QR決済・ローンの各口座を管理します
          </p>
        </div>
        <CreateAccountDialog />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>口座一覧</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>金融機関</TableHead>
                  <TableHead>口座名</TableHead>
                  <TableHead>種別</TableHead>
                  <TableHead>区分</TableHead>
                  <TableHead>残高追跡</TableHead>
                  <TableHead>状態</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading &&
                  Array.from({ length: 3 }).map((_, index) => (
                    <TableRow key={`skeleton-${index}`}>
                      <TableCell colSpan={6}>
                        <Skeleton className="h-6 w-full" />
                      </TableCell>
                    </TableRow>
                  ))}
                {!isLoading && isError && (
                  <TableRow>
                    <TableCell colSpan={6} className="py-8 text-center text-destructive">
                      口座の取得に失敗しました
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading && !isError && accounts && accounts.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                      口座がまだ登録されていません
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading &&
                  !isError &&
                  accounts?.map((account) => (
                    <TableRow key={account.id}>
                      <TableCell>{institutionNameById.get(account.institution_id) ?? '—'}</TableCell>
                      <TableCell>{account.account_name}</TableCell>
                      <TableCell>{ACCOUNT_TYPE_LABELS[account.account_type] ?? account.account_type}</TableCell>
                      <TableCell>{account.is_business ? '事業' : '個人'}</TableCell>
                      <TableCell>{account.tracks_balance ? '追跡する' : '追跡しない'}</TableCell>
                      <TableCell>
                        <IsActiveCell account={account} />
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
