import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency } from '@/lib/format'
import { useCategoryBreakdown } from './queries'

const CHART_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
]

export function CategoryBreakdownChart() {
  const { data, isLoading, isError } = useCategoryBreakdown()
  const chartData = data?.map((item) => ({ ...item, amount: Number(item.amount) }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>カテゴリ別の支出</CardTitle>
      </CardHeader>
      <CardContent className="h-72">
        {isLoading && <Skeleton className="h-full w-full" />}
        {isError && <p className="text-sm text-destructive">データの取得に失敗しました</p>}
        {chartData && chartData.length === 0 && <p className="text-sm text-muted-foreground">今月の支出はまだありません</p>}
        {chartData && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="amount"
                nameKey="category_name"
                innerRadius="55%"
                outerRadius="80%"
                paddingAngle={2}
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={entry.category_id ?? entry.category_name}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => formatCurrency(Number(value))}
                contentStyle={{
                  backgroundColor: 'var(--popover)',
                  borderColor: 'var(--border)',
                  color: 'var(--popover-foreground)',
                  borderRadius: 8,
                }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                wrapperStyle={{ fontSize: 12, color: 'var(--muted-foreground)' }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
