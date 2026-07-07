export interface Account {
  id: number
  account_name: string
  account_type: string
  is_business: boolean
  is_active: boolean
  tracks_balance: boolean
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

export interface Transfer {
  id: number
  from_transaction_id: number
  to_transaction_id: number
  match_confidence: string
  linked_at: string
}

export interface TransferCreate {
  from_transaction_id: number
  to_transaction_id: number
}
