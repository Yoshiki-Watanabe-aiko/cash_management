export type AccountType = 'bank' | 'credit_card' | 'securities' | 'qr_payment' | 'loan'
export type BalanceMethod = 'cumulative' | 'moneyforward' | 'manual'
export type InstitutionType = 'bank' | 'credit_card' | 'securities' | 'qr_payment'

export interface Account {
  id: number
  institution_id: number
  account_name: string
  account_type: AccountType
  is_business: boolean
  is_active: boolean
  default_business_ratio: string
  tracks_balance: boolean
  balance_method: BalanceMethod | null
  opening_balance: string | null
  opening_balance_date: string | null
  moneyforward_account_name: string | null
  card_last4: string | null
}

export interface AccountCreate {
  institution_id: number
  account_name: string
  account_type: AccountType
  is_business?: boolean
  is_active?: boolean
  default_business_ratio?: number
  tracks_balance?: boolean
  balance_method?: BalanceMethod | null
  opening_balance?: number | null
  opening_balance_date?: string | null
  moneyforward_account_name?: string | null
  card_last4?: string | null
}

export interface AccountUpdate {
  institution_id?: number
  account_name?: string
  account_type?: AccountType
  is_business?: boolean
  is_active?: boolean
  default_business_ratio?: number
  tracks_balance?: boolean
  balance_method?: BalanceMethod | null
  opening_balance?: number | null
  opening_balance_date?: string | null
  moneyforward_account_name?: string | null
  card_last4?: string | null
}

export interface Institution {
  id: number
  institution_name: string
  institution_type: InstitutionType
}

export interface Category {
  id: number
  category_name: string
}

// バックエンドはDecimalフィールドをresponse_model経由で精度保持のためJSON文字列として返す
// (jsonable_encoderのfloat変換は通らない)。表示・演算前に必ずNumber()で変換すること。
export interface NetWorthPoint {
  snapshot_date: string
  net_worth: string
}

export interface BudgetProgressItem {
  category_id: number
  category_name: string
  budget_amount: string
  spent_amount: string
  progress_ratio: string
}

export interface CashflowSummary {
  income: string
  expense: string
}

export interface CategoryAmount {
  category_id: number | null
  category_name: string
  amount: string
}

export interface Transaction {
  id: number
  account_id: number | null
  transaction_date: string
  amount: string
  description: string
  category_id: number | null
  business_ratio: string
  source_type: string
  is_transferred: boolean
}

export interface TransactionListResponse {
  items: Transaction[]
  total: number
  page: number
  page_size: number
}

export interface TransactionUpdate {
  category_id?: number | null
  business_ratio?: number | null
}

export interface RecategorizeResult {
  updated_count: number
}

export type MatchConfidence = 'auto' | 'manual'

export interface Transfer {
  id: number
  from_transaction_id: number
  to_transaction_id: number
  match_confidence: MatchConfidence
  linked_at: string
}

export interface TransferCreate {
  from_transaction_id: number
  to_transaction_id: number
}

export interface LinkedTransferTransaction {
  id: number
  transaction_date: string
  amount: string
  description: string
  account_id: number | null
}

export interface LinkedTransfer {
  id: number
  match_confidence: MatchConfidence
  linked_at: string
  from_transaction: LinkedTransferTransaction
  to_transaction: LinkedTransferTransaction
}

export interface Budget {
  id: number
  category_id: number
  year_month: string
  is_business: boolean
  budget_amount: string
}

export interface BudgetCreate {
  category_id: number
  year_month: string
  is_business: boolean
  budget_amount: number
}

export interface BudgetUpdate {
  budget_amount: number
}

export interface CategoryRule {
  id: number
  keyword_pattern: string
  category_id: number
  priority: number
}

export interface CategoryRuleCreate {
  keyword_pattern: string
  category_id: number
  priority: number
}

export interface CategoryRuleUpdate {
  keyword_pattern?: string
  category_id?: number
  priority?: number
}
