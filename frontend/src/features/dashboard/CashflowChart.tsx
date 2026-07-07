import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency } from '@/lib/format'
import { usePersonalCashflow } from './queries'

export function CashflowChart() {
  const { data, isLoading, isError } = usePersonalCashflow()

  const chartData = data
    ? [
        { label: '収入', amount: Number(data.income), fill: 'var(--income)' },
        { label: '支出', amount: Math.abs(Number(data.expense)), fill: 'var(--expense)' },
      ]
    : []

  return (
    <Card>
      <CardHeader>
        <CardTitle>個人口座のキャッシュフロー（今月）</CardTitle>
      </CardHeader>
      <CardContent className="h-64">
        {isLoading && <Skeleton className="h-full w-full" />}
        {isError && <p className="text-sm text-destructive">データの取得に失敗しました</p>}
        {data && (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }} />
              <YAxis
                tickFormatter={(value: number) => formatCurrency(value)}
                width={90}
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
              />
              <Tooltip
                formatter={(value) => formatCurrency(Number(value))}
                contentStyle={{
                  backgroundColor: 'var(--popover)',
                  borderColor: 'var(--border)',
                  color: 'var(--popover-foreground)',
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="amount" radius={[6, 6, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.label} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
