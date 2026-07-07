import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency, formatDate } from '@/lib/format'
import { useNetWorthHistory } from './queries'

export function NetWorthChart() {
  const { data, isLoading, isError } = useNetWorthHistory(12)
  const chartData = data?.map((point) => ({ snapshot_date: point.snapshot_date, net_worth: Number(point.net_worth) }))

  return (
    <Card className="col-span-full lg:col-span-2">
      <CardHeader>
        <CardTitle>純資産の推移</CardTitle>
      </CardHeader>
      <CardContent className="h-72">
        {isLoading && <Skeleton className="h-full w-full" />}
        {isError && <p className="text-sm text-destructive">データの取得に失敗しました</p>}
        {chartData && chartData.length === 0 && (
          <p className="text-sm text-muted-foreground">資産スナップショットがまだありません</p>
        )}
        {chartData && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="snapshot_date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
              />
              <YAxis
                tickFormatter={(value: number) => formatCurrency(value)}
                width={90}
                tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
              />
              <Tooltip
                formatter={(value) => formatCurrency(Number(value))}
                labelFormatter={(label) => formatDate(String(label))}
                contentStyle={{
                  backgroundColor: 'var(--popover)',
                  borderColor: 'var(--border)',
                  color: 'var(--popover-foreground)',
                  borderRadius: 8,
                }}
              />
              <Line
                type="monotone"
                dataKey="net_worth"
                stroke="var(--chart-1)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
