import { describe, expect, it } from 'vitest'
import { formatCurrency, formatDate, formatPercent } from './format'

describe('formatCurrency', () => {
  it('formats a numeric amount as JPY currency', () => {
    expect(formatCurrency(1234)).toBe('￥1,234')
  })

  it('formats a Decimal-as-string amount from the backend as JPY currency', () => {
    // バックエンドのDecimalフィールドはresponse_model経由でJSON文字列として返るため、
    // string入力を正しくNumber()変換して整形できることを確認する。
    expect(formatCurrency('1234')).toBe('￥1,234')
  })

  it('formats a negative amount', () => {
    expect(formatCurrency('-500')).toBe('-￥500')
  })
})

describe('formatPercent', () => {
  it('formats a numeric ratio as a percentage', () => {
    expect(formatPercent(0.5)).toBe('50%')
  })

  it('formats a Decimal-as-string ratio from the backend as a percentage', () => {
    expect(formatPercent('1.234')).toBe('123.4%')
  })
})

describe('formatDate', () => {
  it('converts an ISO date string to slash-separated Japanese format', () => {
    expect(formatDate('2026-07-08')).toBe('2026/07/08')
  })
})
