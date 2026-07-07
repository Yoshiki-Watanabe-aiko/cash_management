import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { formatCurrency, formatPercent } from '@/lib/format'
import { useBudgetProgress } from './queries'

export function BudgetProgressWidget() {
  const { data, isLoading, isError } = useBudgetProgress()

  return (
    <Card>
      <CardHeader>
        <CardTitle>今月の事業経費の進捗</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && (
          <>
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </>
        )}
        {isError && <p className="text-sm text-destructive">データの取得に失敗しました</p>}
        {data && data.length === 0 && <p className="text-sm text-muted-foreground">予算が設定されていません</p>}
        {data?.map((item) => {
          const ratio = Number(item.progress_ratio)
          const isOverBudget = ratio > 1
          return (
            <div key={item.category_id} className="space-y-1.5">
              <div className="flex items-baseline justify-between text-sm">
                <span className="font-medium text-foreground">{item.category_name}</span>
                <span className={cn('tabular-nums', isOverBudget ? 'text-expense' : 'text-muted-foreground')}>
                  {formatCurrency(item.spent_amount)} / {formatCurrency(item.budget_amount)}
                </span>
              </div>
              <Progress
                value={Math.min(ratio, 1) * 100}
                className={cn(isOverBudget && '[&>div]:bg-expense')}
              />
              <p className={cn('text-xs', isOverBudget ? 'text-expense' : 'text-muted-foreground')}>
                {formatPercent(ratio)}
                {isOverBudget && ' 予算超過'}
              </p>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
