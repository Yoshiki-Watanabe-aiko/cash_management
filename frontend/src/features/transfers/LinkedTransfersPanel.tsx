import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ApiError } from '@/api/client'
import { formatCurrency, formatDate } from '@/lib/format'
import { useAccounts } from '@/features/reference/queries'
import { useDeleteTransferLink, useLinkedTransfers } from './queries'

export function LinkedTransfersPanel() {
  const { data: transfers, isLoading, isError } = useLinkedTransfers()
  const { data: accounts } = useAccounts()
  const deleteLink = useDeleteTransferLink()
  const [errorMessage, setErrorMessage] = useState<string>()

  const accountNameById = new Map(accounts?.map((account) => [account.id, account.account_name]))

  const handleUnlink = (id: number) => {
    setErrorMessage(undefined)
    deleteLink.mutate(id, {
      onError: (error) => {
        setErrorMessage(error instanceof ApiError ? error.message : '解除に失敗しました')
      },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>紐づけ済み振替一覧</CardTitle>
        <p className="text-sm text-muted-foreground">誤って紐づけた振替はここから解除できます</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>出金側</TableHead>
                <TableHead>入金側</TableHead>
                <TableHead>紐づけ方式</TableHead>
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
                    振替一覧の取得に失敗しました
                  </TableCell>
                </TableRow>
              )}
              {!isLoading && !isError && transfers && transfers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                    紐づけ済みの振替はありません
                  </TableCell>
                </TableRow>
              )}
              {!isLoading &&
                !isError &&
                transfers?.map((transfer) => (
                  <TableRow key={transfer.id}>
                    <TableCell>
                      {formatDate(transfer.from_transaction.transaction_date)}{' '}
                      {accountNameById.get(transfer.from_transaction.account_id ?? -1) ?? '—'}{' '}
                      {formatCurrency(transfer.from_transaction.amount)} {transfer.from_transaction.description}
                    </TableCell>
                    <TableCell>
                      {formatDate(transfer.to_transaction.transaction_date)}{' '}
                      {accountNameById.get(transfer.to_transaction.account_id ?? -1) ?? '—'}{' '}
                      {formatCurrency(transfer.to_transaction.amount)} {transfer.to_transaction.description}
                    </TableCell>
                    <TableCell>{transfer.match_confidence === 'manual' ? '手動' : '自動'}</TableCell>
                    <TableCell>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        aria-label="振替リンクを解除"
                        onClick={() => handleUnlink(transfer.id)}
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
  )
}
