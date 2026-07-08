import { useId, useState } from 'react'
import { Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError } from '@/api/client'
import { formatCurrency, formatDate } from '@/lib/format'
import { useAccounts } from '@/features/reference/queries'
import { useCreateTransferLink, useUnlinkedTransferCandidates } from './queries'

export function UnlinkedTransfersPanel() {
  const { data: candidates, isLoading, isError } = useUnlinkedTransferCandidates()
  const { data: accounts } = useAccounts()
  const createLink = useCreateTransferLink()

  const fromSelectId = useId()
  const toSelectId = useId()
  const [fromId, setFromId] = useState('')
  const [toId, setToId] = useState('')
  const [errorMessage, setErrorMessage] = useState<string>()

  const accountNameById = new Map(accounts?.map((account) => [account.id, account.account_name]))
  const outgoing = candidates?.filter((txn) => Number(txn.amount) < 0) ?? []
  const incoming = candidates?.filter((txn) => Number(txn.amount) > 0) ?? []

  const describe = (id: string | undefined) => {
    const txn = candidates?.find((candidate) => String(candidate.id) === id)
    if (!txn) return ''
    const accountName = accountNameById.get(txn.account_id ?? -1) ?? '—'
    return `${formatDate(txn.transaction_date)} ${accountName} ${formatCurrency(txn.amount)} ${txn.description}`
  }

  const handleLink = () => {
    if (!fromId || !toId) return
    setErrorMessage(undefined)
    createLink.mutate(
      { from_transaction_id: Number(fromId), to_transaction_id: Number(toId) },
      {
        onSuccess: () => {
          setFromId('')
          setToId('')
        },
        onError: (error) => {
          setErrorMessage(error instanceof ApiError ? error.message : '紐づけに失敗しました')
        },
      },
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>振替の手動紐づけ</CardTitle>
        <p className="text-sm text-muted-foreground">
          直近7日以内の未紐づけ取引から、出金側と入金側を選んで手動でリンクできます（金額完全一致・営業日0〜3日以内のみ検証）。
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && <Skeleton className="h-24 w-full" />}
        {isError && <p className="text-sm text-destructive">候補取引の取得に失敗しました</p>}
        {!isLoading && candidates && candidates.length === 0 && (
          <p className="text-sm text-muted-foreground">未紐づけの候補取引はありません</p>
        )}
        {!isLoading && candidates && candidates.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor={fromSelectId}>出金側</Label>
                <Select value={fromId} onValueChange={setFromId}>
                  <SelectTrigger id={fromSelectId} className="w-full">
                    <SelectValue placeholder="出金取引を選択" />
                  </SelectTrigger>
                  <SelectContent>
                    {outgoing.map((txn) => (
                      <SelectItem key={txn.id} value={String(txn.id)}>
                        {formatDate(txn.transaction_date)} {accountNameById.get(txn.account_id ?? -1) ?? '—'}{' '}
                        {formatCurrency(txn.amount)} {txn.description}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor={toSelectId}>入金側</Label>
                <Select value={toId} onValueChange={setToId}>
                  <SelectTrigger id={toSelectId} className="w-full">
                    <SelectValue placeholder="入金取引を選択" />
                  </SelectTrigger>
                  <SelectContent>
                    {incoming.map((txn) => (
                      <SelectItem key={txn.id} value={String(txn.id)}>
                        {formatDate(txn.transaction_date)} {accountNameById.get(txn.account_id ?? -1) ?? '—'}{' '}
                        {formatCurrency(txn.amount)} {txn.description}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {fromId && toId && (
              <p className="text-sm text-muted-foreground">
                {describe(fromId)} → {describe(toId)}
              </p>
            )}

            {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

            <Button type="button" onClick={handleLink} disabled={!fromId || !toId || createLink.isPending}>
              <Link2 />
              紐づける
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
