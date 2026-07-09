import { Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { AccountsPage } from '@/features/accounts/AccountsPage'
import { BudgetsPage } from '@/features/budgets/BudgetsPage'
import { CategoryRulesPage } from '@/features/category-rules/CategoryRulesPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { TransactionsPage } from '@/features/transactions/TransactionsPage'

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="budgets" element={<BudgetsPage />} />
        <Route path="category-rules" element={<CategoryRulesPage />} />
        <Route path="accounts" element={<AccountsPage />} />
      </Route>
    </Routes>
  )
}

export default App
