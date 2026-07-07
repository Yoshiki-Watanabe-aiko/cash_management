import { BudgetProgressWidget } from './BudgetProgressWidget'
import { CashflowChart } from './CashflowChart'
import { CategoryBreakdownChart } from './CategoryBreakdownChart'
import { NetWorthChart } from './NetWorthChart'

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">ダッシュボード</h1>
        <p className="text-sm text-muted-foreground">資産と収支の状況をひと目で確認できます</p>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <NetWorthChart />
        <BudgetProgressWidget />
        <CashflowChart />
        <CategoryBreakdownChart />
      </div>
    </div>
  )
}
